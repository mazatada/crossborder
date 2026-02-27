from flask import Blueprint, request, jsonify
from app.db import db
from app.models import WebhookEndpoint, WebhookDLQ
from app.audit import record_event
import secrets
from datetime import datetime
from app.auth import require_api_key

bp = Blueprint("v1_webhooks", __name__, url_prefix="/v1/integrations")


@bp.post("/webhooks")
@require_api_key
def register_webhook():
    """Register a new webhook endpoint"""
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")

    url = data.get("url")
    events = data.get("events", [])

    if not url or not isinstance(url, str):
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "INVALID_ARGUMENT", "message": "url is required"},
                }
            ),
            400,
        )

    if not events or not isinstance(events, list):
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "INVALID_ARGUMENT",
                        "message": "events must be a non-empty list",
                    },
                }
            ),
            400,
        )

    # Generate a secure random secret
    secret = secrets.token_urlsafe(32)

    webhook = WebhookEndpoint(url=url, secret=secret, events=events, active=True)

    db.session.add(webhook)
    db.session.commit()

    if trace_id:
        record_event(
            event="WEBHOOK_REGISTERED",
            trace_id=trace_id,
            webhook_id=webhook.id,
            url=url,
        )

    return (
        jsonify(
            {
                "id": webhook.id,
                "url": webhook.url,
                "secret": webhook.secret,  # Return secret only on creation
                "events": webhook.events,
                "active": webhook.active,
                "created_at": webhook.created_at.isoformat(),
            }
        ),
        201,
    )


@bp.get("/webhooks")
@require_api_key
def list_webhooks():
    """List all registered webhooks"""
    webhooks = db.session.query(WebhookEndpoint).filter_by(active=True).all()

    return (
        jsonify(
            {
                "webhooks": [
                    {
                        "id": w.id,
                        "url": w.url,
                        "events": w.events,
                        "active": w.active,
                        "created_at": w.created_at.isoformat(),
                    }
                    for w in webhooks
                ]
            }
        ),
        200,
    )


@bp.delete("/webhooks/<int:webhook_id>")
@require_api_key
def delete_webhook(webhook_id: int):
    """Delete (deactivate) a webhook endpoint"""
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")

    webhook = db.session.query(WebhookEndpoint).filter_by(id=webhook_id).first()

    if not webhook:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
                }
            ),
            404,
        )

    webhook.active = False
    db.session.commit()

    if trace_id:
        record_event(event="WEBHOOK_DELETED", trace_id=trace_id, webhook_id=webhook_id)

    return jsonify({"status": "success", "id": webhook_id}), 200


@bp.post("/webhooks/<int:webhook_id>/test")
@require_api_key
def test_webhook(webhook_id: int):
    """Test webhook delivery with a sample payload"""
    from app.integrations.webhook_dispatcher import dispatch_webhook

    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")

    webhook = (
        db.session.query(WebhookEndpoint).filter_by(id=webhook_id, active=True).first()
    )

    if not webhook:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
                }
            ),
            404,
        )

    # Send test event
    test_payload = {
        "event": "WEBHOOK_TEST",
        "trace_id": trace_id or "TEST",
        "timestamp": "2025-12-03T23:00:00Z",
        "data": {"message": "This is a test webhook"},
    }

    result = dispatch_webhook(webhook, test_payload)

    return (
        jsonify(
            {
                "status": "success",
                "webhook_id": webhook_id,
                "delivery_status": result.get("status"),
                "response": result,
            }
        ),
        200,
    )


@bp.get("/webhooks/dlq")
@require_api_key
def list_dlq():
    """List all DLQ entries"""
    dlq_entries = (
        db.session.query(WebhookDLQ)
        .filter_by(replayed=False)
        .order_by(WebhookDLQ.created_at.desc())
        .all()
    )

    return (
        jsonify(
            {
                "dlq_entries": [
                    {
                        "id": entry.id,
                        "webhook_id": entry.webhook_id,
                        "event_type": entry.event_type,
                        "trace_id": entry.trace_id,
                        "attempts": entry.attempts,
                        "last_error": entry.last_error,
                        "last_status_code": entry.last_status_code,
                        "created_at": entry.created_at.isoformat(),
                        "expires_at": entry.expires_at.isoformat(),
                    }
                    for entry in dlq_entries
                ]
            }
        ),
        200,
    )


@bp.post("/webhooks/dlq/<int:dlq_id>/replay")
@require_api_key
def replay_dlq(dlq_id: int):
    """Manually replay a DLQ entry"""
    from app.integrations.webhook_dispatcher import dispatch_webhook

    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")

    dlq_entry = db.session.query(WebhookDLQ).filter_by(id=dlq_id).first()

    if not dlq_entry:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "NOT_FOUND", "message": "DLQ entry not found"},
                }
            ),
            404,
        )

    if dlq_entry.replayed:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {
                        "code": "ALREADY_REPLAYED",
                        "message": "This entry has already been replayed",
                    },
                }
            ),
            400,
        )

    # Get webhook
    webhook = (
        db.session.query(WebhookEndpoint).filter_by(id=dlq_entry.webhook_id).first()
    )
    if not webhook:
        return (
            jsonify(
                {
                    "status": "error",
                    "error": {"code": "NOT_FOUND", "message": "Webhook not found"},
                }
            ),
            404,
        )

    # Replay the webhook
    result = dispatch_webhook(webhook, dlq_entry.payload)

    # Mark as replayed if successful
    if result.get("success"):
        dlq_entry.replayed = True
        db.session.commit()

    if trace_id:
        record_event(
            event="DLQ_REPLAYED",
            trace_id=trace_id,
            dlq_id=dlq_id,
            success=result.get("success"),
        )

    return (
        jsonify(
            {
                "status": "success",
                "dlq_id": dlq_id,
                "replayed": result.get("success"),
                "response": result,
            }
        ),
        200,
    )


@bp.post("/webhooks/dlq/cleanup")
@require_api_key
def cleanup_dlq():
    """Clean up expired DLQ entries (72 hours old)"""
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")

    now = datetime.utcnow()
    expired_entries = (
        db.session.query(WebhookDLQ).filter(WebhookDLQ.expires_at < now).all()
    )

    count = len(expired_entries)
    for entry in expired_entries:
        db.session.delete(entry)

    db.session.commit()

    if trace_id:
        record_event(event="DLQ_CLEANUP", trace_id=trace_id, deleted_count=count)

    return jsonify({"status": "success", "deleted_count": count}), 200
