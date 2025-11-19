# app/jobs/cli.py
import os
import sys
import time
import json
import traceback
from datetime import datetime, timezone, timedelta

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import db
from app.models import Job
from app.audit import record_event
from app.webhook import post_event
from app.jobs.handlers import clearance_pack, pn_submit
from app.jobs import handlers as job_handlers

REGISTRY = dict(job_handlers.REGISTRY)

# echo は内蔵（互換）
def _handle_echo(payload: dict, *, job_id: int, trace_id: str):
    return {"ok": True, "job_id": job_id, "echo": payload, "trace_id": trace_id or None}

WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))
SCHEDULER_INTERVAL_SEC = int(os.getenv("SCHEDULER_INTERVAL_SEC", "10"))
VISIBILITY_TIMEOUT_SEC = int(os.getenv("VISIBILITY_TIMEOUT_SEC", "1800"))
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
PICK_BATCH = int(os.getenv("PICK_BATCH", "10"))

def _now_utc():
    return datetime.now(timezone.utc)

def _log(**kw):
    kw.setdefault("ts", _now_utc().isoformat())
    print(json.dumps(kw, ensure_ascii=False), flush=True)

def _db_session():
    from app.factory import create_app
    app = create_app()
    return app.app_context(), db.session

def scheduler_tick(session):
    try:
        n1 = session.execute(text("""
            UPDATE jobs
            SET status = 'queued', updated_at = now()
            WHERE status = 'retrying'
              AND (next_run_at IS NULL OR next_run_at <= now());
        """)).rowcount

        n2 = session.execute(text(f"""
            UPDATE jobs
            SET status = 'retrying', next_run_at = now() + interval '30 seconds', updated_at = now()
            WHERE status = 'running'
              AND updated_at <= (now() - interval '{VISIBILITY_TIMEOUT_SEC} seconds');
        """)).rowcount

        session.commit()
        _log(event="SCHEDULER_TICK", queued_from_retrying=n1, retried_from_running=n2)
    except SQLAlchemyError as e:
        session.rollback()
        _log(level="error", event="SCHEDULER_ERROR", error=str(e))

def scheduler_loop():
    ctx, session = _db_session()
    with ctx:
        _log(event="SCHEDULER_START", interval_sec=SCHEDULER_INTERVAL_SEC)
        while True:
            scheduler_tick(session)
            time.sleep(SCHEDULER_INTERVAL_SEC)

def pick_batch(session, batch=PICK_BATCH):
    rows = session.execute(text("""
        WITH cte AS (
          SELECT id
          FROM jobs
          WHERE status IN ('queued','retrying')
            AND (next_run_at IS NULL OR next_run_at <= now())
          ORDER BY next_run_at NULLS FIRST, id
          FOR UPDATE SKIP LOCKED
          LIMIT :batch
        )
        UPDATE jobs j
        SET status='running', attempts=j.attempts+1, updated_at=now()
        FROM cte
        WHERE j.id = cte.id
        RETURNING j.id;
    """), {"batch": batch}).fetchall()

    ids = [r[0] for r in rows]
    if not ids:
        session.commit()
        return []

    jobs = session.query(Job).filter(Job.id.in_(ids)).all()
    session.commit()
    return jobs

def _next_backoff(attempt: int, base=30, factor=2, jitter=0.2):
    import random
    sec = base * (factor ** max(0, attempt - 1))
    j = sec * jitter
    return timedelta(seconds=int(sec + random.uniform(-j, j)))

def _complete(session, job: Job, result: dict):
    job.status = "succeeded"
    job.result_json = result
    job.next_run_at = None
    job.updated_at = _now_utc()
    session.add(job)

def _after_success(job, result):
    # イベント名はジョブタイプに応じて変換
    event_type = {
      "clearance_pack": "DOCS_PACKAGED",
      "pn_submit": "PN_SUBMITTED",
    }.get(job.type, f"JOB_{job.type.upper()}_SUCCEEDED")

    payload = {
        "job_id": job.id,
        "event_type": event_type,
        "occurred_at": job.updated_at.isoformat() if getattr(job, "updated_at", None) else None,
        "trace_id": job.trace_id,
        "result": result,
    }
    resp = post_event(event_type, payload, trace_id=job.trace_id)
    record_event(event="WEBHOOK_POST", trace_id=job.trace_id or "", payload={
        "url": os.getenv("WEBHOOK_URL",""),
        "status": resp.get("status"),
        "latency_ms": resp.get("latency_ms"),
        "event_type": event_type,
        "job_id": job.id,
    })
    
def _schedule_retry(session, job: Job, err: dict):
    job.status = "retrying"
    job.error = err
    job.next_run_at = _now_utc() + _next_backoff(job.attempts + 1)
    job.updated_at = _now_utc()
    session.add(job)

def _fail(session, job: Job, err: dict):
    job.status = "failed"
    job.error = err
    job.updated_at = _now_utc()
    session.add(job)

def dispatch(job: Job):
    handler = REGISTRY.get(job.type)
    if not handler:
        if job.type == "echo":
            handler = _handle_echo
        else:
            raise RuntimeError(f"No handler registered for type={job.type}")
    payload = job.payload_json or {}
    trace_id = job.trace_id or ""
    return handler(payload, job_id=job.id, trace_id=trace_id)

def worker_once(session):
    batch = pick_batch(session)
    if not batch:
        time.sleep(0.5)
        return 0

    done = 0
    for job in batch:
        t0 = time.time()
        try:
            # 1) ハンドラ実行
            result = dispatch(job)

            # 2) 成功として確定（DB書き込み）
            _complete(session, job, result)
            session.commit()  # ← 先に確定（ここまでは元のまま）

            # 3) ★成功後フック：Webhook送信＋監査記録
            _after_success(job, result)  # ← この1行を追加したため、ここが新しい

            # 4) 監査イベント（本処理とは独立トランザクションでOK）
            record_event(
                event="JOB_SUCCEEDED",
                trace_id=job.trace_id,
                target_type="job",
                target_id=job.id,
                type=job.type,
            )
            _log(event="JOB_SUCCEEDED", job_id=job.id, type=job.type,
                 latency_ms=int((time.time() - t0) * 1000))
            done += 1

        except Exception as e:
            # 失敗時：元の挙動を維持
            session.rollback()
            err = {
                "class": e.__class__.__name__,
                "message": str(e),
                "traceback": traceback.format_exc().splitlines()[-5:],
            }
            try:
                if job.attempts < MAX_ATTEMPTS:
                    _schedule_retry(session, job, err)
                    session.commit()
                    record_event(
                        event="JOB_RETRYING",
                        trace_id=job.trace_id,
                        target_type="job",
                        target_id=job.id,
                        type=job.type,
                        attempts=job.attempts,
                        error_class=err["class"],
                        error_message=err["message"],
                    )
                    _log(level="warning", event="JOB_RETRYING", job_id=job.id, type=job.type,
                         attempts=job.attempts, error=err["message"])
                else:
                    _fail(session, job, err)
                    session.commit()
                    record_event(
                        event="JOB_FAILED",
                        trace_id=job.trace_id,
                        target_type="job",
                        target_id=job.id,
                        type=job.type,
                        attempts=job.attempts,
                        error_class=err["class"],
                        error_message=err["message"],
                    )
                    _log(level="error", event="JOB_FAILED", job_id=job.id, type=job.type,
                         attempts=job.attempts, error=err["message"])
            except Exception as e2:
                session.rollback()
                _log(level="error", event="JOB_STATUS_WRITE_FAILED", job_id=job.id, error=str(e2))
    return done

def worker_loop():
    ctx, session = _db_session()
    with ctx:
        _log(event="HANDLERS", names=sorted(REGISTRY.keys()))
        _log(event="WORKER_START", concurrency=WORKER_CONCURRENCY)
        while True:
            n = worker_once(session)
            if n == 0:
                time.sleep(0.2)

def _get_mode():
    # 1) 環境変数 MODE
    m = os.getenv("MODE", "").strip().lower()
    if m:
        return m
    # 2) CLI引数 --mode worker|scheduler にも対応
    if "--mode" in sys.argv:
        try:
            idx = sys.argv.index("--mode")
            return sys.argv[idx + 1].strip().lower()
        except Exception:
            return ""
    return ""

def main():
    mode = _get_mode()
    if mode == "worker":
        worker_loop()
    else:
        scheduler_loop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        _log(event="SHUTDOWN", reason="KeyboardInterrupt")
        sys.exit(0)
