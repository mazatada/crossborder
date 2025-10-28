# app/jobs/cli.py
import os
import sys
import time
import json
import traceback
import app.jobs.handlers.clearance_pack  # noqa: F401
import app.jobs.handlers.pn_submit       # noqa: F401
from datetime import datetime, timezone, timedelta
from app.jobs.handlers import REGISTRY  # これが本体のレジストリ

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import db
from app.models import Job

# --- ハンドラレジストリ -----------------------------------------------------
#   REGISTRY に { "job_type": callable(payload, *, job_id, trace_id) -> dict } を登録


# サイドエフェクト import（@register で自動登録される想定のもの）
# これらは存在しなくても構いません（無ければスキップされます）
try:
    import app.jobs.handlers.clearance_pack  # noqa: F401
except Exception:
    pass

try:
    import app.jobs.handlers.pn_submit  # noqa: F401
except Exception:
    pass

def _log(**kw):
    ...
    print(json.dumps(kw, ensure_ascii=False), flush=True)

# 起動時に登録済みハンドラ名を出して可視化（デバッグ用）
_log(event="HANDLERS", names=sorted(REGISTRY.keys()))

# echo は内蔵（互換のため）
def _handle_echo(payload: dict, *, job_id: int, trace_id: str):
    return {"ok": True, "job_id": job_id, "echo": payload, "trace_id": trace_id or None}


# --- 設定値 ---------------------------------------------------------------
WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))
SCHEDULER_INTERVAL_SEC = int(os.getenv("SCHEDULER_INTERVAL_SEC", "10"))
VISIBILITY_TIMEOUT_SEC = int(os.getenv("VISIBILITY_TIMEOUT_SEC", "1800"))  # 30分
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))

# --- ユーティリティ ---------------------------------------------------------
def _now_utc():
    return datetime.now(timezone.utc)

def _log(**kw):
    # 最低限の構造化ログ（stdout）
    kw.setdefault("ts", _now_utc().isoformat())
    print(json.dumps(kw, ensure_ascii=False), flush=True)

def _db_session():
    # フラスクのアプリコンテキスト経由で db.session を使う想定
    from app.factory import create_app
    app = create_app()
    # アプリコンテキストが必要
    return app.app_context(), db.session

# --- スケジューラ -----------------------------------------------------------
def scheduler_tick(session):
    """
    - next_run_at に到達した retrying を queued へ戻す
    - visibility timeout を超えた running を retrying へ戻す（簡易）
    """
    try:
        # retrying -> queued
        n1 = session.execute(text("""
            UPDATE jobs
            SET status = 'queued', updated_at = now()
            WHERE status = 'retrying'
              AND (next_run_at IS NULL OR next_run_at <= now());
        """)).rowcount

        # visibility timeout: running で updated_at が古すぎるものを retrying に
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

# --- ワーカー ---------------------------------------------------------------
PICK_BATCH = int(os.getenv("PICK_BATCH", "10"))

def pick_batch(session, batch=PICK_BATCH):
    """
    FOR UPDATE SKIP LOCKED で安全にバッチ取得し、running に更新して返す
    """
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
    # 例: 1→30s, 2→60s, 3→120s
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
    """
    REGISTRY を見てハンドラを呼ぶ。無ければ echo をフォールバック。
    """
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
            result = dispatch(job)
            _complete(session, job, result)
            session.commit()
            _log(event="JOB_SUCCEEDED", job_id=job.id, type=job.type, latency_ms=int((time.time()-t0)*1000))
            done += 1
        except Exception as e:
            session.rollback()
            err = {
                "class": e.__class__.__name__,
                "message": str(e),
                "traceback": traceback.format_exc().splitlines()[-5:],
            }
            if job.attempts < MAX_ATTEMPTS:
                try:
                    _schedule_retry(session, job, err)
                    session.commit()
                    _log(level="warning", event="JOB_RETRYING", job_id=job.id, type=job.type,
                         attempts=job.attempts, error=err["message"])
                except Exception as e2:
                    session.rollback()
                    _log(level="error", event="JOB_RETRY_SCHEDULE_FAILED", job_id=job.id, error=str(e2))
            else:
                try:
                    _fail(session, job, err)
                    session.commit()
                    _log(level="error", event="JOB_FAILED", job_id=job.id, type=job.type, attempts=job.attempts, error=err["message"])
                except Exception as e3:
                    session.rollback()
                    _log(level="error", event="JOB_FAIL_WRITE_FAILED", job_id=job.id, error=str(e3))
    return done

def worker_loop():
    ctx, session = _db_session()
    with ctx:
        _log(event="WORKER_START", concurrency=WORKER_CONCURRENCY)
        # 単純なシングルプロセス・ループ（コンテナ1プロセス想定）
        while True:
            n = worker_once(session)
            if n == 0:
                time.sleep(0.2)

# --- エントリーポイント -----------------------------------------------------
def main():
    mode = os.getenv("MODE", "").strip().lower()
    if mode == "worker":
        worker_loop()
    else:
        # MODE 未設定時は scheduler
        scheduler_loop()

if __name__ == "__main__":
    # コンテナの CMD/entrypoint から `python -m app.jobs.cli` として呼ばれる想定
    try:
        main()
    except KeyboardInterrupt:
        _log(event="SHUTDOWN", reason="KeyboardInterrupt")
        sys.exit(0)
