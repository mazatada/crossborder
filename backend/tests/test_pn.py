import pytest
from sqlalchemy import delete

from app.db import db
from app.models import Job


@pytest.fixture(scope="module", autouse=True)
def ensure_tables():
    db.metadata.create_all(bind=db.engine)
    yield
    db.session.execute(delete(Job))
    db.session.commit()


@pytest.mark.integration
def test_prior_notice_queues_job_and_records_event(client, monkeypatch):
    calls = []

    def _record_event(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.api.v1_pn.record_event", _record_event)

    payload = {
        "traceId": "pn-trace-1",
        "product": {"name": "Sample Food", "category": "Snack"},
        "logistics": {"arrival": "2025-12-01T00:00:00Z"},
        "importer": {"name": "Importer Inc."},
        "consignee": {"name": "Consignee LLC"},
    }
    response = client.post("/v1/fda/prior-notice", json=payload)
    assert response.status_code == 202
    job_id = response.get_json()["job_id"]

    job = db.session.get(Job, job_id)
    assert job is not None
    assert job.type == "pn_submit"
    assert job.trace_id == "pn-trace-1"
    assert job.payload_json["product"]["name"] == "Sample Food"

    assert len(calls) == 1
    assert calls[0]["event"] == "JOB_QUEUED"
    assert calls[0]["trace_id"] == "pn-trace-1"

    db.session.delete(job)
    db.session.commit()


@pytest.mark.integration
def test_prior_notice_missing_required_fields(client):
    response = client.post("/v1/fda/prior-notice", json={})
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.integration
def test_worker_processes_prior_notice_job(monkeypatch):
    from datetime import datetime, timedelta
    from app.models import Job
    from app.jobs import cli

    record_calls = []
    webhook_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)

    def _post_event(event_type, payload, trace_id=None):
        webhook_calls.append(
            {"event_type": event_type, "payload": payload, "trace_id": trace_id}
        )
        return {"status": 200, "latency_ms": 5}

    monkeypatch.setattr("app.jobs.cli.record_event", _record_event)
    monkeypatch.setattr("app.jobs.cli.post_event", _post_event)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={
            "traceId": "pn-trace-worker",
            "product": {"name": "Sample", "category": "Snack"},
            "logistics": {"arrival": "2025-12-01T00:00:00Z"},
            "importer": {"name": "Importer Inc."},
            "consignee": {"name": "Consignee LLC"},
        },
        trace_id="pn-trace-worker",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    job = db.session.get(Job, job.id)
    assert job.status == "succeeded"
    assert job.result_json["receipt_media_id"] == "dev:pn-receipt"

    assert webhook_calls[0]["event_type"] == "PN_SUBMITTED"
    assert record_calls[0]["event"] == "WEBHOOK_POST"
    assert record_calls[1]["event"] == "JOB_SUCCEEDED"

    db.session.delete(job)
    db.session.commit()
