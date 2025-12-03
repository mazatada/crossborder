from flask import Blueprint, request, jsonify
from app.db import db
from app.models import WebhookEndpoint
from app.audit import record_event
import secrets

bp = Blueprint("v1_webhooks", __name__, url_prefix="/v1/integrations")


@bp.post("/webhooks")
def register_webhook():
    """Register a new webhook endpoint"""
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    
    url = data.get("url")
    events = data.get("events", [])
    
    if not url or not isinstance(url, str):
        return jsonify({"status": "error", "error": {"code": "INVALID_ARGUMENT", "message": "url is required"}}), 400
    
    if not events or not isinstance(events, list):
        return jsonify({"status": "error", "error": {"code": "INVALID_ARGUMENT", "message": "events must be a non-empty list"}}), 400
    
    # Generate a secure random secret
    secret = secrets.token_urlsafe(32)
    
    webhook = WebhookEndpoint(
        url=url,
        secret=secret,
        events=events,
        active=True
    )
    
    db.session.add(webhook)
    db.session.commit()
    
    if trace_id:
        record_event(event="WEBHOOK_REGISTERED", trace_id=trace_id, webhook_id=webhook.id, url=url)
    
    return jsonify({
        "id": webhook.id,
        "url": webhook.url,
        "secret": webhook.secret,  # Return secret only on creation
        "events": webhook.events,
        "active": webhook.active,
        "created_at": webhook.created_at.isoformat()
    }), 201


@bp.get("/webhooks")
def list_webhooks():
    """List all registered webhooks"""
    webhooks = db.session.query(WebhookEndpoint).filter_by(active=True).all()
    
    return jsonify({
        "webhooks": [
            {
                "id": w.id,
                "url": w.url,
                "events": w.events,
                "active": w.active,
                "created_at": w.created_at.isoformat()
            } for w in webhooks
        ]
    }), 200


@bp.delete("/webhooks/<int:webhook_id>")
def delete_webhook(webhook_id: int):
    """Delete (deactivate) a webhook endpoint"""
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    
    webhook = db.session.query(WebhookEndpoint).filter_by(id=webhook_id).first()
    
    if not webhook:
        return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Webhook not found"}}), 404
    
    webhook.active = False
    db.session.commit()
    
    if trace_id:
        record_event(event="WEBHOOK_DELETED", trace_id=trace_id, webhook_id=webhook_id)
    
    return jsonify({"status": "success", "id": webhook_id}), 200


@bp.post("/webhooks/<int:webhook_id>/test")
def test_webhook(webhook_id: int):
    """Test webhook delivery with a sample payload"""
    from app.integrations.webhook_dispatcher import dispatch_webhook
    
    data = request.get_json(silent=True) or {}
    trace_id = data.get("traceId")
    
    webhook = db.session.query(WebhookEndpoint).filter_by(id=webhook_id, active=True).first()
    
    if not webhook:
        return jsonify({"status": "error", "error": {"code": "NOT_FOUND", "message": "Webhook not found"}}), 404
    
    # Send test event
    test_payload = {
        "event": "WEBHOOK_TEST",
        "trace_id": trace_id or "TEST",
        "timestamp": "2025-12-03T23:00:00Z",
        "data": {"message": "This is a test webhook"}
    }
    
    result = dispatch_webhook(webhook, test_payload)
    
    return jsonify({
        "status": "success",
        "webhook_id": webhook_id,
        "delivery_status": result.get("status"),
        "response": result
    }), 200
