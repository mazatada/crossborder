import pytest
from app.models import AuditEvent
from app.db import db


@pytest.fixture
def audit_data():
    # Clean up before
    db.session.query(AuditEvent).delete()
    db.session.commit()

    # Insert dummy data
    events = [
        AuditEvent(trace_id="trace-1", event="JOB_QUEUED", payload={"job": 1}),
        AuditEvent(trace_id="trace-1", event="JOB_SUCCEEDED", payload={"job": 1}),
        AuditEvent(trace_id="trace-2", event="WEBHOOK_POST", payload={"status": 200}),
    ]
    db.session.add_all(events)
    db.session.commit()
    yield
    # Cleanup after
    db.session.query(AuditEvent).delete()
    db.session.commit()


@pytest.mark.integration
def test_audit_trace(client, audit_data):
    resp = client.get("/v1/audit/trace/trace-1")
    assert resp.status_code == 200
    data = resp.json
    assert len(data["events"]) == 2
    assert data["events"][0]["event"] == "JOB_QUEUED"
    assert data["events"][1]["event"] == "JOB_SUCCEEDED"


@pytest.mark.integration
def test_audit_recent(client, audit_data):
    resp = client.get("/v1/audit/recent?limit=2")
    assert resp.status_code == 200
    data = resp.json
    assert len(data["events"]) == 2
    # Recent should be trace-2 (latest) then trace-1 (second latest)
    # Note: ID order depends on insertion, but usually sequential
    assert data["events"][0]["trace_id"] == "trace-2"
    assert data["events"][1]["trace_id"] == "trace-1"
