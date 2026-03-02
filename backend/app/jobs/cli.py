# app/jobs/cli.py
import os
import sys
import time
import threading
import json
import traceback
from datetime import datetime, timezone, timedelta

import datetime as dt
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError

from typing import Any, Dict, Optional

from app.db import db
from app.models import Job
from app.audit import record_event
from app.webhook import post_event
from app.jobs import handlers as job_handlers

REGISTRY = dict(job_handlers.REGISTRY)


class NonRetriableError(Exception):
    """Raise from handlers to mark job as failed without retry."""


class RetryableError(Exception):
    """Raise from handlers to trigger retry with custom backoff."""

    def __init__(self, message: str, backoff_sec: float = 60):
        super().__init__(message)
        self.backoff_sec = backoff_sec


# echo は内蔵（互換）
def _handle_echo(payload: dict, *, job_id: int, trace_id: str):
    return {"ok": True, "job_id": job_id, "echo": payload, "trace_id": trace_id or None}


WORKER_CONCURRENCY = int(os.getenv("WORKER_CONCURRENCY", "4"))
SCHEDULER_INTERVAL_SEC = int(os.getenv("SCHEDULER_INTERVAL_SEC", "10"))
VISIBILITY_TIMEOUT_SEC = int(os.getenv("VISIBILITY_TIMEOUT_SEC", "1800"))
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
PICK_BATCH = int(os.getenv("PICK_BATCH", "10"))
WEBHOOK_RETRY_MAX_ATTEMPTS = int(os.getenv("WEBHOOK_RETRY_MAX_ATTEMPTS", "5"))
WEBHOOK_RETRY_BASE_SEC = int(os.getenv("WEBHOOK_RETRY_BASE_SEC", "30"))


def _now_utc():
    return datetime.now(timezone.utc)


def _log(**kw):
    kw.setdefault("ts", _now_utc().isoformat())
    from app.logging_conf import get_trace_id
    tid = get_trace_id()
    if tid:
        kw.setdefault("trace_id", tid)
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _db_session():
    from app.factory import create_app

    app = create_app()
    return app.app_context(), db.session


def _is_sqlite(session) -> bool:
    return session.get_bind().dialect.name == "sqlite"


def scheduler_tick(session):
    is_sq = _is_sqlite(session)
    now_func = "CURRENT_TIMESTAMP" if is_sq else "now()"
    try:
        n1 = session.execute(
            text(
                f"""
            UPDATE jobs
            SET status = 'queued', updated_at = {now_func}
            WHERE status = 'retrying'
              AND (next_run_at IS NULL OR next_run_at <= {now_func});
        """
            )
        ).rowcount

        if is_sq:
            n2_sql = f"""
            UPDATE jobs
            SET status = 'retrying', next_run_at = datetime(CURRENT_TIMESTAMP, '+30 seconds'), updated_at = CURRENT_TIMESTAMP
            WHERE status = 'running'
              AND updated_at <= datetime(CURRENT_TIMESTAMP, '-{VISIBILITY_TIMEOUT_SEC} seconds');
            """
        else:
            n2_sql = f"""
            UPDATE jobs
            SET status = 'retrying', next_run_at = now() + interval '30 seconds', updated_at = now()
            WHERE status = 'running'
              AND updated_at <= (now() - interval '{VISIBILITY_TIMEOUT_SEC} seconds');
            """

        n2 = session.execute(text(n2_sql)).rowcount

        session.commit()
        _log(event="SCHEDULER_TICK", queued_from_retrying=n1, retried_from_running=n2)
    except SQLAlchemyError as e:
        session.rollback()
        _log(level="error", event="SCHEDULER_ERROR", error=str(e))


def _cleanup_old_data(session):
    try:
        from app.models import WebhookDLQ, AuditEvent
        now = _now_utc()
        
        dlq_ids = [r[0] for r in session.query(WebhookDLQ.id).filter(WebhookDLQ.expires_at < now).limit(500).all()]
        if dlq_ids:
            session.query(WebhookDLQ).filter(WebhookDLQ.id.in_(dlq_ids)).delete(synchronize_session=False)

        limit_date = now - timedelta(days=90)
        audit_deleted_count = 0
        try:
            # Using ORM prevents raw SQL dialect differences and avoids locks by limiting batch size
            audit_ids = [r[0] for r in session.query(AuditEvent.id).filter(AuditEvent.ts < limit_date).limit(1000).all()]
            if audit_ids:
                session.query(AuditEvent).filter(AuditEvent.id.in_(audit_ids)).delete(synchronize_session=False)
                audit_deleted_count = len(audit_ids)
        except SQLAlchemyError:
            session.rollback()
            # Split-brain fallback: If 'ts' doesn't exist, the table was created by audit.py with 'at' column
            is_sq = _is_sqlite(session)
            tbl = "audit_events" if is_sq else "public.audit_events"
            rows = session.execute(text(f"SELECT id FROM {tbl} WHERE at < :limit_date LIMIT 1000"), {"limit_date": limit_date}).fetchall()
            ids = [r[0] for r in rows]
            if ids:
                bind_placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
                bind_params = {f"id_{i}": val for i, val in enumerate(ids)}
                session.execute(text(f"DELETE FROM {tbl} WHERE id IN ({bind_placeholders})"), bind_params)
                audit_deleted_count = len(ids)
            
        if dlq_ids or audit_deleted_count > 0:
            session.commit()
            _log(event="CLEANUP_TICK", dlq_deleted=len(dlq_ids), audit_deleted=audit_deleted_count)
    except Exception as e:
        session.rollback()
        _log(level="error", event="CLEANUP_ERROR", error=str(e))


def _cleanup_loop():
    """Independent daemon thread loop for executing DB cleanup without blocking the main scheduler."""
    while True:
        try:
            ctx, session = _db_session()
            with ctx:
                _cleanup_old_data(session)
        except Exception as e:
            _log(level="error", event="CLEANUP_LOOP_CRASH", error=str(e))
        # Run cleanup once an hour
        time.sleep(3600)


def scheduler_loop():
    # Spawn the cleanup job independently so it doesn't cause head-of-line blocking in the scheduler
    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()

    ctx, session = _db_session()
    with ctx:
        _log(event="SCHEDULER_START", interval_sec=SCHEDULER_INTERVAL_SEC)
        while True:
            scheduler_tick(session)
            time.sleep(SCHEDULER_INTERVAL_SEC)


def pick_batch(session, batch=PICK_BATCH):
    if _is_sqlite(session):
        sql_sel = text(
            "SELECT id FROM jobs WHERE status IN ('queued','retrying') AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP) ORDER BY next_run_at ASC LIMIT :batch"
        )
        rows = session.execute(sql_sel, {"batch": batch}).fetchall()
        if not rows:
            session.commit()
            return []
        ids = [r[0] for r in rows]
        bind_placeholders = ", ".join(f":id_{i}" for i in range(len(ids)))
        bind_params = {f"id_{i}": job_id for i, job_id in enumerate(ids)}
        sql_upd = text(
            f"UPDATE jobs SET status='running', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP WHERE id IN ({bind_placeholders})"
        )
        session.execute(sql_upd, bind_params)
    else:
        rows = session.execute(
            text(
                """
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
        """
            ),
            {"batch": batch},
        ).fetchall()
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


def _heartbeat(session, job: Job):
    job.updated_at = _now_utc()
    session.add(job)
    session.commit()


def _after_success(job, result):
    # イベント名はジョブタイプに応じて変換
    event_type = {
        "clearance_pack": "DOCS_PACKAGED",
        "pn_submit": "PN_SUBMITTED",
    }.get(job.type, f"JOB_{job.type.upper()}_SUCCEEDED")

    payload = {
        "event_id": str(job.id),
        "event_type": event_type,
        "occurred_at": (
            job.updated_at.isoformat() if getattr(job, "updated_at", None) else None
        ),
        "trace_id": job.trace_id or "",
        "result": result,
    }
    try:
        resp = post_event(event_type, payload, trace_id=job.trace_id)
        status = resp.get("status")
        if not isinstance(status, int) or status >= 500:
            raise RuntimeError(f"webhook status {status}")
        record_event(
            event="WEBHOOK_POST",
            trace_id=job.trace_id,
            payload={
                "url": os.getenv("WEBHOOK_URL", ""),
                "status": resp.get("status"),
                "latency_ms": resp.get("latency_ms"),
                "event_type": event_type,
                "job_id": job.id,
            },
        )
    except Exception as e:
        err = {"class": e.__class__.__name__, "message": str(e)}
        _log(
            level="error",
            event="WEBHOOK_POST_FAILED",
            job_id=job.id,
            type=job.type,
            error=err["message"],
        )
        # webhook_retry 自身は再送ジョブを作らず、監査だけ残す
        if job.type == "webhook_retry":
            try:
                record_event(
                    event="WEBHOOK_POST_FAILED",
                    trace_id=job.trace_id,
                    target_type="job",
                    target_id=job.id,
                    type=job.type,
                    error_class=err["class"],
                    error_message=err["message"],
                )
            except Exception:
                _log(
                    level="error",
                    event="AUDIT_LOG_FAILED",
                    job_id=job.id,
                    type=job.type,
                    reason="record_event failed after webhook failure",
                )
            return
        try:
            retry_job = Job(
                type="webhook_retry",
                status="queued",
                attempts=0,
                next_run_at=func.now(),
                payload_json={
                    "event_type": event_type,
                    "payload": payload,
                    "trace_id": job.trace_id,
                    "retry_max_attempts": WEBHOOK_RETRY_MAX_ATTEMPTS,
                    "retry_base_sec": WEBHOOK_RETRY_BASE_SEC,
                },
                trace_id=job.trace_id,
            )
            db.session.add(retry_job)
            db.session.commit()
            _log(
                event="WEBHOOK_RETRY_ENQUEUED",
                job_id=job.id,
                retry_job_id=retry_job.id,
                event_type=event_type,
            )
            record_event(
                event="WEBHOOK_POST_FAILED",
                trace_id=job.trace_id,
                target_type="job",
                target_id=job.id,
                type=job.type,
                error_class=err["class"],
                error_message=err["message"],
                retry_job_id=retry_job.id,
            )
        except Exception as e2:
            db.session.rollback()
            _log(
                level="error",
                event="WEBHOOK_RETRY_ENQUEUE_FAILED",
                job_id=job.id,
                type=job.type,
                error=str(e2),
            )
            try:
                record_event(
                    event="WEBHOOK_RETRY_ENQUEUE_FAILED",
                    trace_id=job.trace_id,
                    target_type="job",
                    target_id=job.id,
                    type=job.type,
                    error_message=str(e2),
                )
            except Exception:
                _log(
                    level="error",
                    event="AUDIT_LOG_FAILED",
                    job_id=job.id,
                    type=job.type,
                    reason="record_event failed after webhook failure",
                )


def _schedule_retry(session, job: Job, err: dict, backoff_sec: Optional[float] = None):
    job.status = "retrying"
    job.error = err
    if backoff_sec is not None:
        job.next_run_at = _now_utc() + dt.timedelta(seconds=backoff_sec)
    else:
        job.next_run_at = _now_utc() + _next_backoff(job.attempts + 1)
    job.updated_at = _now_utc()
    session.add(job)


def _fail(session, job: Job, err: dict):
    job.status = "failed"
    job.error = err
    job.updated_at = _now_utc()
    session.add(job)


def _after_failure(job: Job, err: dict):
    # Send a webhook notification about the permanent failure
    payload = {
        "event_id": str(job.id),
        "event_type": "JOB_FAILED",
        "occurred_at": job.updated_at.isoformat(),
        "trace_id": job.trace_id or "",
        "error": {
            "code": err.get("class", "UNKNOWN_ERROR"),
            "message": err.get("message", "Unknown error occurred"),
        },
    }

    try:
        # Ignore response, as the job is already failing.
        # This will not retry within the worker itself.
        post_event("JOB_FAILED", payload, trace_id=job.trace_id)
    except Exception as e:
        _log(
            level="error",
            event="WEBHOOK_POST_FAILED",
            job_id=job.id,
            type=job.type,
            error=str(e),
            note="Failed to send webhook for JOB_FAILED event",
        )


def requeue_job(job_id: int, *, session=None):
    sess = session or db.session
    job = sess.get(Job, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    job.status = "queued"
    job.error = None
    job.next_run_at = _now_utc()
    job.updated_at = _now_utc()
    job.attempts = 0
    sess.add(job)
    sess.commit()
    record_event(
        event="JOB_REQUEUED",
        trace_id=job.trace_id,
        target_type="job",
        target_id=job.id,
        type=job.type,
    )
    return job


def cancel_job(job_id: int, *, session=None):
    sess = session or db.session
    job = sess.get(Job, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")
    job.status = "canceled"
    job.next_run_at = None
    job.updated_at = _now_utc()
    sess.add(job)
    sess.commit()
    record_event(
        event="JOB_CANCELED",
        trace_id=job.trace_id,
        target_type="job",
        target_id=job.id,
        type=job.type,
    )
    return job


def dispatch(job: Job):
    handler = REGISTRY.get(job.type)
    if not handler:
        if job.type == "echo":
            handler = _handle_echo
        else:
            raise NonRetriableError(f"No handler registered for type={job.type}")
    payload: Dict[str, Any] = job.payload_json or {}
    # attempts は job.attempts を真実源とし、handler へ引き渡す
    payload["_job_attempts"] = job.attempts
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
        
        token = None
        from app.logging_conf import set_trace_id, reset_trace_id
        if job.trace_id:
            token = set_trace_id(job.trace_id)
            
        try:
            # 0) ハートビートを先に刻んで可視性タイムアウトを延長
            _heartbeat(session, job)

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
            _log(
                event="JOB_SUCCEEDED",
                job_id=job.id,
                type=job.type,
                latency_ms=int((time.time() - t0) * 1000),
            )
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
                if isinstance(e, NonRetriableError):
                    _fail(session, job, err)
                    session.commit()
                    _after_failure(job, err)
                    record_event(
                        event="JOB_FAILED",
                        trace_id=job.trace_id,
                        target_type="job",
                        target_id=job.id,
                        type=job.type,
                        attempts=job.attempts,
                        error_class=err["class"],
                        error_message=err["message"],
                        retriable=False,
                    )
                    _log(
                        level="error",
                        event="JOB_FAILED",
                        job_id=job.id,
                        type=job.type,
                        attempts=job.attempts,
                        error=err["message"],
                        retriable=False,
                    )
                elif isinstance(e, RetryableError):
                    # Use custom backoff from RetryableError
                    _schedule_retry(session, job, err, backoff_sec=e.backoff_sec)
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
                        backoff_sec=e.backoff_sec,
                    )
                    _log(
                        level="warning",
                        event="JOB_RETRYING",
                        job_id=job.id,
                        type=job.type,
                        attempts=job.attempts,
                        error=err["message"],
                        backoff_sec=e.backoff_sec,
                    )
                else:
                    # Default retry
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
                        _log(
                            level="warning",
                            event="JOB_RETRYING",
                            job_id=job.id,
                            type=job.type,
                            attempts=job.attempts,
                            error=err["message"],
                        )
                    else:
                        _fail(session, job, err)
                        session.commit()
                        _after_failure(job, err)
                        record_event(
                            event="JOB_FAILED",
                            trace_id=job.trace_id,
                            target_type="job",
                            target_id=job.id,
                            type=job.type,
                            attempts=job.attempts,
                            error_class=err["class"],
                            error_message=err["message"],
                            retriable=True,
                        )
                        _log(
                            level="error",
                            event="JOB_FAILED",
                            job_id=job.id,
                            type=job.type,
                            attempts=job.attempts,
                            error=err["message"],
                            retriable=True,
                        )
            except Exception as e2:
                session.rollback()
                _log(
                    level="error",
                    event="JOB_STATUS_WRITE_FAILED",
                    job_id=job.id,
                    error=str(e2),
                )
        finally:
            if token:
                reset_trace_id(token)

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
    from app.logging_conf import setup_logging
    setup_logging()
    
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
