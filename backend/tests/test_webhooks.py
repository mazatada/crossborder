import pytest
import json
import hmac
import hashlib
from app.integrations.hmac_utils import generate_signature, verify_signature
from app.models import WebhookEndpoint, OrderStatus
from app.db import db


def test_hmac_signature_generation():
    """Test HMAC signature generation"""
    payload = {"event": "TEST", "data": {"value": 123}}
    secret = "test-secret"
    
    signature = generate_signature(payload, secret)
    
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest length


def test_hmac_signature_verification():
    """Test HMAC signature verification"""
    payload = {"event": "TEST", "data": {"value": 123}}
    secret = "test-secret"
    
    signature = generate_signature(payload, secret)
    
    # Valid signature
    assert verify_signature(payload, signature, secret) is True
    
    # Invalid signature
    assert verify_signature(payload, "invalid-signature", secret) is False
    
    # Wrong secret
    assert verify_signature(payload, signature, "wrong-secret") is False


def test_register_webhook(client):
    """Test webhook registration"""
    resp = client.post("/v1/integrations/webhooks", json={
        "url": "https://example.com/webhook",
        "events": ["HS_CLASSIFIED", "DOCS_PACKAGED"],
        "traceId": "TEST-TRACE-001"
    })
    
    assert resp.status_code == 201
    data = resp.get_json()
    assert "id" in data
    assert data["url"] == "https://example.com/webhook"
    assert data["events"] == ["HS_CLASSIFIED", "DOCS_PACKAGED"]
    assert "secret" in data  # Secret should be returned on creation
    assert data["active"] is True


def test_register_webhook_invalid_url(client):
    """Test webhook registration with invalid URL"""
    resp = client.post("/v1/integrations/webhooks", json={
        "events": ["HS_CLASSIFIED"]
    })
    
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"


def test_list_webhooks(client):
    """Test listing webhooks"""
    # Register a webhook first
    client.post("/v1/integrations/webhooks", json={
        "url": "https://example.com/webhook1",
        "events": ["HS_CLASSIFIED"]
    })
    
    resp = client.get("/v1/integrations/webhooks")
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert "webhooks" in data
    assert len(data["webhooks"]) >= 1
    # Secret should NOT be returned in list
    assert "secret" not in data["webhooks"][0]


def test_delete_webhook(client):
    """Test webhook deletion"""
    # Register a webhook
    create_resp = client.post("/v1/integrations/webhooks", json={
        "url": "https://example.com/webhook",
        "events": ["HS_CLASSIFIED"]
    })
    webhook_id = create_resp.get_json()["id"]
    
    # Delete it
    resp = client.delete(f"/v1/integrations/webhooks/{webhook_id}", json={
        "traceId": "TEST-TRACE-002"
    })
    
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    
    # Verify it's deactivated
    webhook = db.session.query(WebhookEndpoint).filter_by(id=webhook_id).first()
    assert webhook.active is False


def test_webhook_signature_in_dispatcher(client, monkeypatch):
    """Test that webhook dispatcher includes correct signature"""
    from app.integrations import webhook_dispatcher
    import requests
    
    # Mock requests.post
    called_with = {}
    def mock_post(url, json, headers, timeout):
        called_with["url"] = url
        called_with["json"] = json
        called_with["headers"] = headers
        
        class MockResponse:
            status_code = 200
            text = "OK"
        return MockResponse()
    
    monkeypatch.setattr(requests, "post", mock_post)
    
    # Create webhook
    webhook = WebhookEndpoint(
        id=1,
        url="https://example.com/webhook",
        secret="test-secret",
        events=["TEST"],
        active=True
    )
    
    payload = {"event": "TEST", "trace_id": "TEST-001"}
    
    result = webhook_dispatcher.dispatch_webhook(webhook, payload)
    
    assert result["status"] == 200
    assert "X-Signature" in called_with["headers"]
    
    # Verify signature is correct
    signature = called_with["headers"]["X-Signature"]
    assert verify_signature(payload, signature, "test-secret") is True
