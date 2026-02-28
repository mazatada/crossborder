# app/jobs/handlers/webhook_dispatch.py
"""
Outbox パターンで起票された webhook_dispatch ジョブを処理するハンドラ。
各 WebhookEndpoint へ HMAC 署名付き HTTP POST を実施する。
失敗時はリトライパスに載せ、最終的に DLQ へ退避する。
"""
import json
import hmac
import hashlib
import time
from urllib import request as urllib_request, error as urllib_error
from typing import Optional

from . import register
from app.audit import record_event


def _sign(body: bytes, secret: str) -> str:
    """HMAC-SHA256 署名を生成"""
    mac = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def _http_post(
    url: str,
    payload_dict: dict,
    secret: str,
    event_type: str,
    trace_id: Optional[str] = None,
    timeout: float = 10.0,
) -> dict:
    """標準ライブラリのみで JSON POST（requests 不要）"""
    body = json.dumps(payload_dict, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    headers = {
        "Content-Type": "application/json",
        "X-Event-Type": event_type,
        "X-Signature": _sign(body, secret),
        "User-Agent": "Crossborder-Webhook/1.0",
    }
    if trace_id:
        headers["X-Trace-ID"] = trace_id

    req = urllib_request.Request(url, data=body, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib_request.urlopen(req, timeout=timeout) as resp:
            status = resp.getcode()
    except urllib_error.HTTPError as e:
        status = e.code
    except Exception as e:
        return {
            "status": None,
            "error": str(e),
            "latency_ms": int((time.time() - t0) * 1000),
        }
    latency_ms = int((time.time() - t0) * 1000)
    return {"status": status, "latency_ms": latency_ms}


@register("webhook_dispatch")
def handle(payload: dict, *, job_id: int, trace_id: str) -> dict:
    from app.jobs.cli import NonRetriableError, RetryableError, _next_backoff
    from app.db import db
    from app.models import WebhookDLQ
    from datetime import datetime, timedelta

    endpoint_url = payload.get("endpoint_url", "")
    endpoint_secret = payload.get("endpoint_secret", "")
    endpoint_id = payload.get("endpoint_id")
    event_type = payload.get("event_type", "unknown")
    event_payload = payload.get("payload", {})
    target_trace = payload.get("payload", {}).get("trace_id") or trace_id

    retry_max = payload.get("retry_max_attempts", 5)
    retry_base = payload.get("retry_base_sec", 30)

    # 実行回数は Job.attempts を真実源とする
    attempt = int(payload.get("_job_attempts") or 0)

    if not endpoint_url:
        return {"skipped": True, "reason": "endpoint_url not set"}

    # --- HTTP POST 実行 ---
    resp = _http_post(
        url=endpoint_url,
        payload_dict=event_payload,
        secret=endpoint_secret,
        event_type=event_type,
        trace_id=target_trace,
    )

    status = resp.get("status")

    # --- 成功 ---
    if isinstance(status, int) and 200 <= status < 300:
        record_event(
            event="WEBHOOK_DISPATCHED",
            trace_id=target_trace,
            target_type="webhook_endpoint",
            target_key=str(endpoint_id) if endpoint_id else None,
            event_type=event_type,
            status_code=status,
            latency_ms=resp.get("latency_ms"),
        )
        return {
            "status": status,
            "trace_id": target_trace,
            "event_type": event_type,
            "endpoint_id": endpoint_id,
        }

    # --- 失敗 (5xx or connection error) ---
    error_msg = resp.get("error") or f"HTTP {status}"

    if attempt >= retry_max:
        # DLQ に退避
        if endpoint_id:
            try:
                dlq_entry = WebhookDLQ(
                    webhook_id=endpoint_id,
                    event_type=event_type,
                    payload=event_payload,
                    trace_id=target_trace,
                    attempts=attempt,
                    last_error=error_msg,
                    last_status_code=status,
                    expires_at=datetime.utcnow() + timedelta(hours=72),
                )
                db.session.add(dlq_entry)
                db.session.commit()
            except Exception:
                db.session.rollback()
        record_event(
            event="WEBHOOK_DISPATCH_DLQ",
            trace_id=target_trace,
            target_type="webhook_endpoint",
            target_key=str(endpoint_id) if endpoint_id else None,
            event_type=event_type,
            error=error_msg,
            attempts=attempt,
        )
        raise NonRetriableError(
            f"webhook dispatch exhausted ({attempt} attempts), moved to DLQ"
        )

    # リトライ
    backoff = _next_backoff(attempt + 1, base=retry_base)
    raise RetryableError(
        f"Webhook dispatch returned {status}, retrying in {backoff.total_seconds()}s",
        backoff_sec=backoff.total_seconds(),
    )
