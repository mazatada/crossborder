from . import register
from app.webhook import post_event


@register("webhook_retry")
def handle(payload: dict, *, job_id: int, trace_id: str):
    from app.jobs.cli import NonRetriableError, _next_backoff  # late import to avoid circular

    event_type = payload.get("event_type")
    event_payload = payload.get("payload")
    target_trace = payload.get("trace_id") or trace_id
    # attempts は Job.attempts を真実源とする（dispatch で _job_attempts を付与）
    attempt = int(payload.get("_job_attempts") or 0)
    try:
        resp = post_event(event_type, event_payload, trace_id=target_trace)
    except Exception as e:
        resp = {"status": 503, "error": str(e)}

    retry_max = payload.get("retry_max_attempts", 5)
    retry_base = payload.get("retry_base_sec", 30)
    if resp.get("status") and resp["status"] >= 500:
        if attempt >= retry_max:
            raise NonRetriableError("webhook retry exhausted")
        backoff = _next_backoff(attempt + 1, base=retry_base)
        return {
            "retry": True,
            "backoff_sec": backoff.total_seconds(),
            "trace_id": target_trace,
            "event_type": event_type,
        }

    return {"status": resp.get("status"), "trace_id": target_trace, "event_type": event_type}
