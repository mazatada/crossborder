# backend/app/webhook.py
import os
import hmac
import hashlib
import json
import time
from urllib import request, error

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
TIMEOUT = float(os.getenv("WEBHOOK_TIMEOUT_SEC", "3"))


def _signature(body: bytes) -> str:
    mac = hmac.new(WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={mac}"


def post_event(event_type: str, payload: dict, trace_id: str | None = None) -> dict:
    """
    標準ライブラリのみでJSON POST。requests不要。
    戻り値: {"status": HTTPステータスコード, "latency_ms": int} / 失敗時 {"status": None, "error": "..."}
    """
    if not WEBHOOK_URL:
        return {"skipped": True, "reason": "WEBHOOK_URL not set"}
    if not WEBHOOK_SECRET:
        return {"skipped": True, "reason": "WEBHOOK_SECRET not set"}

    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
        "utf-8"
    )
    headers = {
        "Content-Type": "application/json",
        "X-Event-Type": event_type,
        "X-Signature": _signature(body),
    }
    if trace_id:
        headers["X-Trace-ID"] = trace_id

    req = request.Request(WEBHOOK_URL, data=body, headers=headers, method="POST")

    t0 = time.time()
    try:
        with request.urlopen(req, timeout=TIMEOUT) as resp:
            status = resp.getcode()
    except error.HTTPError as e:
        # サーバがエラー応答を返した場合もHTTPコードを返す
        status = e.code
    except Exception as e:
        return {"status": None, "error": str(e)}
    latency_ms = int((time.time() - t0) * 1000)
    return {"status": status, "latency_ms": latency_ms}
