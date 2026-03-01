from app.models import OrderStatus
from app.db import db


def test_receive_order_status_paid(client):
    """Test receiving PAID order status"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-123/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={"status": "PAID", "ts": "2025-12-03T10:00:00Z", "customer_region": "US"},
    )

    assert resp.status_code == 202
    data = resp.get_json()
    assert data["status"] == "accepted"
    assert data["order_id"] == "ORDER-123"

    # Verify database record
    order_status = db.session.query(OrderStatus).filter_by(order_id="ORDER-123").first()
    assert order_status is not None
    assert order_status.status == "PAID"
    assert order_status.customer_region == "US"


def test_receive_order_status_canceled(client):
    """Test receiving CANCELED order status"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-456/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={"status": "CANCELED", "ts": "2025-12-03T11:00:00Z"},
    )

    assert resp.status_code == 202


def test_receive_order_status_invalid_api_key(client):
    """Test rejection with invalid API key"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-789/status",
        headers={"Authorization": "Bearer wrong-key"},
        json={"status": "PAID", "ts": "2025-12-03T12:00:00Z"},
    )

    assert resp.status_code == 401
    data = resp.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_receive_order_status_missing_api_key(client):
    """Test rejection when API key is missing"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-999/status",
        json={"status": "PAID", "ts": "2025-12-03T13:00:00Z"},
    )

    assert resp.status_code == 401


def test_receive_order_status_invalid_status(client):
    """Test validation of status enum"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-111/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={"status": "INVALID_STATUS", "ts": "2025-12-03T14:00:00Z"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"


def test_receive_order_status_missing_timestamp(client):
    """Test validation of required timestamp"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-222/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={"status": "PAID"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"
    assert "ts" in data["error"]["message"]


def test_receive_order_status_invalid_timestamp_format(client):
    """Test validation of timestamp format"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-333/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={"status": "PAID", "ts": "not-a-timestamp"},
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"
    assert "ISO 8601" in data["error"]["message"]


def test_receive_order_status_invalid_customer_region(client):
    """Test validation of customer_region"""
    resp = client.post(
        "/v1/integrations/orders/ORDER-REGION-1/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "status": "PAID",
            "ts": "2025-12-03T10:00:00Z",
            "customer_region": "JPN",
        },  # 3 chars
    )

    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["code"] == "INVALID_ARGUMENT"
    assert "ISO 3166-1 alpha-2" in data["error"]["message"]

    resp2 = client.post(
        "/v1/integrations/orders/ORDER-REGION-2/status",
        headers={"Authorization": "Bearer test-api-key"},
        json={
            "status": "PAID",
            "ts": "2025-12-03T10:00:00Z",
            "customer_region": "us",
        },  # Lowercase
    )

    assert resp2.status_code == 400
    data2 = resp2.get_json()
    assert data2["error"]["code"] == "INVALID_ARGUMENT"
    assert "ISO 3166-1 alpha-2" in data2["error"]["message"]
