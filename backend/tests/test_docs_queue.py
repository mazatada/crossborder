import pytest

from app.db import db
from app.models import Job


@pytest.mark.integration
def test_docs_clearance_pack_queues_job(client, monkeypatch):
    monkeypatch.setattr("app.api.v1_docs.record_event", lambda **kwargs: None)

    payload = {
        "traceId": "test-trace",
        "hs_code": "1905.90",
        "required_uom": "kg",
        "invoice_uom": "kg",
    }
    response = client.post(
        "/v1/docs/clearance-pack",
        headers={"Idempotency-Key": "test-docs-queue-001"},
        json=payload,
    )
    assert response.status_code == 202
    data = response.get_json()
    assert data["status"] == "queued"
    job = db.session.get(Job, data["job_id"])
    assert job is not None
    assert job.type == "clearance_pack"
    assert job.payload_json["hs_code"] == "1905.90"
    db.session.delete(job)
    db.session.commit()


@pytest.mark.integration
def test_docs_clearance_pack_records_event_and_trace_id(client, monkeypatch):
    calls = []

    def _record_event(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.api.v1_docs.record_event", _record_event)

    payload = {
        "traceId": "trace-event",
        "hs_code": "1905.90",
        "required_uom": "kg",
        "invoice_uom": "kg",
        "invoice_payload": {"lines": [{"sku": "ABC", "qty": 1}]},
    }
    response = client.post(
        "/v1/docs/clearance-pack",
        headers={"Idempotency-Key": "test-docs-queue-002"},
        json=payload,
    )
    assert response.status_code == 202
    job_id = response.get_json()["job_id"]

    job = db.session.get(Job, job_id)
    assert job.trace_id == "trace-event"
    assert job.payload_json["invoice_payload"]["lines"][0]["sku"] == "ABC"

    assert len(calls) == 1
    assert calls[0]["event"] == "JOB_QUEUED"
    assert calls[0]["trace_id"] == "trace-event"

    db.session.delete(job)
    db.session.commit()


@pytest.mark.integration
def test_docs_clearance_pack_rejects_missing_fields(client):
    response = client.post(
        "/v1/docs/clearance-pack",
        headers={"Idempotency-Key": "test-docs-queue-003"},
        json={},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
