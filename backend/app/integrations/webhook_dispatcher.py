import requests
from typing import Dict, Any
from app.models import WebhookEndpoint
from app.integrations.hmac_utils import generate_signature, canonicalize_payload
from app.audit import record_event


def dispatch_webhook(
    webhook: WebhookEndpoint, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Dispatch a webhook with HMAC signature.

    Args:
        webhook: WebhookEndpoint model instance
        payload: Event payload to send

    Returns:
        Dictionary with status and response details
    """
    # Generate signature
    signature = generate_signature(payload, webhook.secret)

    # Canonicalize payload for transmission to ensure it matches signature
    payload_str = canonicalize_payload(payload)

    headers = {
        "Content-Type": "application/json",
        "X-Signature": signature,
        "User-Agent": "Crossborder-Webhook/1.0",
    }

    try:
        response = requests.post(
            webhook.url, data=payload_str, headers=headers, timeout=10
        )

        result = {
            "status": response.status_code,
            "success": 200 <= response.status_code < 300,
            "response_body": response.text[:500],  # Truncate for safety
        }

        # Record audit event
        if payload.get("trace_id"):
            record_event(
                event="WEBHOOK_DISPATCHED",
                trace_id=payload["trace_id"],
                webhook_id=webhook.id,
                status_code=response.status_code,
            )

        return result

    except requests.exceptions.Timeout:
        return {"status": 504, "success": False, "error": "Timeout"}
    except requests.exceptions.RequestException as e:
        return {"status": 503, "success": False, "error": str(e)}
