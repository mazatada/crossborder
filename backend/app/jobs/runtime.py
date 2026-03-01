from datetime import timedelta
import os
import random
from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB


class JobError(Exception):
    def __init__(self, message, retriable=True, code="E500_JOB", details=None):
        super().__init__(message)
        self.retriable = retriable
        self.code = code
        self.details = details or {}

    def to_json(self):
        return {
            "class": self.code,
            "message": str(self),
            "retriable": self.retriable,
            "details": self.details,
        }


MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
BACKOFF_BASE = int(os.getenv("BACKOFF_BASE_SEC", "30"))
BACKOFF_FACTOR = float(os.getenv("BACKOFF_FACTOR", "2"))
BACKOFF_JITTER = float(os.getenv("BACKOFF_JITTER", "0.2"))


def next_backoff(attempt: int) -> timedelta:
    base = BACKOFF_BASE * (BACKOFF_FACTOR ** max(0, attempt - 1))
    jitter = base * BACKOFF_JITTER
    return timedelta(seconds=int(base + random.uniform(-jitter, jitter)))


def _is_sqlite(session) -> bool:
    return session.get_bind().dialect.name == "sqlite"

def pick_batch(session, batch: int = 1):
    if _is_sqlite(session):
        # SQLite: シンプルにSELECTしてからUPDATE (FOR UPDATE SKIP LOCKEDやRETURNINGは非同期同時実行以外なら問題ないため使わない)
        sql_sel = text("SELECT id, type, payload_json, trace_id, attempts FROM jobs WHERE status IN ('queued','retrying') AND (next_run_at IS NULL OR next_run_at <= CURRENT_TIMESTAMP) ORDER BY next_run_at ASC LIMIT :batch")
        rows = session.execute(sql_sel, {"batch": batch}).mappings().all()
        if not rows:
            return []
        job_ids = [r["id"] for r in rows]
        bind_placeholders = ", ".join(f":id_{i}" for i in range(len(job_ids)))
        bind_params = {f"id_{i}": j_id for i, j_id in enumerate(job_ids)}
        sql_upd = text(f"UPDATE jobs SET status='running', attempts=attempts+1, updated_at=CURRENT_TIMESTAMP WHERE id IN ({bind_placeholders})")
        session.execute(sql_upd, bind_params)
        # 返り値は j.id, j.type, j.payload_json, j.trace_id, j.attempts となるように合わせる
        updated_rows = []
        for r in rows:
            updated_rows.append(dict(r, attempts=r["attempts"] + 1))
        return updated_rows

    sql = text(
        """
    WITH cte AS (
      SELECT id
        FROM public.jobs
       WHERE status IN ('queued','retrying')
         AND (next_run_at IS NULL OR next_run_at <= now())
       ORDER BY next_run_at NULLS FIRST, id
       FOR UPDATE SKIP LOCKED
       LIMIT :batch
    )
    UPDATE public.jobs AS j
       SET status='running', attempts=j.attempts+1, updated_at=now()
      FROM cte
     WHERE j.id = cte.id
    RETURNING j.id, j.type, j.payload_json, j.trace_id, j.attempts
    """
    )
    return session.execute(sql, {"batch": batch}).mappings().all()

def complete(session, job_id, result_json):
    is_sq = _is_sqlite(session)
    now_func = "CURRENT_TIMESTAMP" if is_sq else "now()"
    tbl = "jobs" if is_sq else "public.jobs"
    sql = text(
        f"""
        UPDATE {tbl}
           SET status='succeeded',
               result_json=:res,
               next_run_at=NULL,
               error=NULL,
               updated_at={now_func}
         WHERE id=:id
    """
    )
    if not is_sq:
        sql = sql.bindparams(bindparam("res", type_=JSONB))
    session.execute(sql, {"res": result_json if is_sq else result_json, "id": job_id})


def schedule_retry(session, job_id, err: JobError, attempts: int):
    is_sq = _is_sqlite(session)
    now_func = "CURRENT_TIMESTAMP" if is_sq else "now()"
    tbl = "jobs" if is_sq else "public.jobs"
    backoff = next_backoff(attempts)
    
    if is_sq:
        next_run = f"datetime(CURRENT_TIMESTAMP, '+{int(backoff.total_seconds())} seconds')"
    else:
        next_run = "now() + (:sec * interval '1 second')"

    sql = text(
        f"""
        UPDATE {tbl}
           SET status='retrying',
               error=:err,
               next_run_at={next_run},
               updated_at={now_func}
         WHERE id=:id
    """
    )
    if not is_sq:
        sql = sql.bindparams(bindparam("err", type_=JSONB))
        session.execute(sql, {"err": err.to_json(), "sec": backoff.total_seconds(), "id": job_id})
    else:
        session.execute(sql, {"err": str(err.to_json()), "id": job_id})


def fail(session, job_id, err: JobError):
    is_sq = _is_sqlite(session)
    now_func = "CURRENT_TIMESTAMP" if is_sq else "now()"
    tbl = "jobs" if is_sq else "public.jobs"
    sql = text(
        f"""
        UPDATE {tbl}
           SET status='failed',
               error=:err,
               next_run_at=NULL,
               updated_at={now_func}
         WHERE id=:id
    """
    )
    if not is_sq:
        sql = sql.bindparams(bindparam("err", type_=JSONB))
        session.execute(sql, {"err": err.to_json(), "id": job_id})
    else:
        session.execute(sql, {"err": str(err.to_json()), "id": job_id})
