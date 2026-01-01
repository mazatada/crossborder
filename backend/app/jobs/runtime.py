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


def pick_batch(session, batch: int = 1):
    sql = text(
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
    UPDATE jobs AS j
       SET status='running', attempts=j.attempts+1, updated_at=now()
      FROM cte
     WHERE j.id = cte.id
    RETURNING j.id, j.type, j.payload_json, j.trace_id, j.attempts
    """
    )
    return session.execute(sql, {"batch": batch}).mappings().all()


def complete(session, job_id, result_json):
    sql = text(
        """
        UPDATE jobs
           SET status='succeeded',
               result_json=:res,
               next_run_at=NULL,
               error=NULL,
               updated_at=now()
         WHERE id=:id
    """
    ).bindparams(
        bindparam("res", type_=JSONB)  # 明示 JSONB
    )
    session.execute(sql, {"res": result_json, "id": job_id})


def schedule_retry(session, job_id, err: JobError, attempts: int):
    backoff = next_backoff(attempts)
    sql = text(
        """
        UPDATE jobs
           SET status='retrying',
               error=:err,
               next_run_at=now() + (:sec * interval '1 second'),
               updated_at=now()
         WHERE id=:id
    """
    ).bindparams(
        bindparam("err", type_=JSONB)  # 明示 JSONB
    )
    session.execute(
        sql, {"err": err.to_json(), "sec": backoff.total_seconds(), "id": job_id}
    )


def fail(session, job_id, err: JobError):
    sql = text(
        """
        UPDATE jobs
           SET status='failed',
               error=:err,
               next_run_at=NULL,
               updated_at=now()
         WHERE id=:id
    """
    ).bindparams(
        bindparam("err", type_=JSONB)  # 明示 JSONB
    )
    session.execute(sql, {"err": err.to_json(), "id": job_id})
