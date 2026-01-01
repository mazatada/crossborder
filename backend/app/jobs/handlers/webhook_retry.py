from . import register
from app.webhook import post_event


@register("webhook_retry")
def handle(payload: dict, *, job_id: int, trace_id: str):
    from app.jobs.cli import (
        NonRetriableError,
        _next_backoff,
    )  # late import to avoid circular
    from app.db import db
    from app.models import WebhookDLQ
    from datetime import datetime, timedelta

    event_type = payload.get("event_type")
    event_payload = payload.get("payload")
    target_trace = payload.get("trace_id") or trace_id
    webhook_id = payload.get("webhook_id")
    # attempts は Job.attempts を真実源とする（dispatch で _job_attempts を付与）
    attempt = int(payload.get("_job_attempts") or 0)
    try:
        # 型チェックとキャスト
        if not isinstance(event_type, str):
            event_type = str(event_type) if event_type else "unknown"
        if not isinstance(event_payload, dict):
            event_payload = {}

        resp = post_event(event_type, event_payload, trace_id=target_trace)
    except Exception as e:
        resp = {"status": 503, "error": str(e)}

    retry_max = payload.get("retry_max_attempts", 5)
    retry_base = payload.get("retry_base_sec", 30)
    if resp.get("status") and resp["status"] >= 500:
        if attempt >= retry_max:
            # Move to DLQ
            if webhook_id:
                dlq_entry = WebhookDLQ(
                    webhook_id=webhook_id,
                    event_type=event_type,
                    payload=event_payload,
                    trace_id=target_trace,
                    attempts=attempt,
                    last_error=resp.get("error", "Unknown error"),
                    last_status_code=resp.get("status"),
                    expires_at=datetime.utcnow() + timedelta(hours=72),
                )
                db.session.add(dlq_entry)
                db.session.commit()
            raise NonRetriableError("webhook retry exhausted, moved to DLQ")
        # Raise to trigger retry path in worker
        from app.jobs.cli import RetryableError

        backoff = _next_backoff(attempt + 1, base=retry_base)
        raise RetryableError(
            f"Webhook returned {resp['status']}, retrying in {backoff.total_seconds()}s",
            backoff_sec=backoff.total_seconds(),
        )

    return {
        "status": resp.get("status"),
        "trace_id": target_trace,
        "event_type": event_type,
    }
