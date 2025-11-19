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
def test_docs_clearance_pack_queues_job(client, monkeypatch):
    monkeypatch.setattr("app.api.v1_docs.record_event", lambda **kwargs: None)

    payload = {
        "traceId": "test-trace",
        "hs_code": "1905.90",
        "required_uom": "kg",
        "invoice_uom": "kg",
    }
    response = client.post("/v1/docs/clearance-pack", json=payload)
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
def test_docs_clearance_pack_rejects_missing_fields(client):
    response = client.post("/v1/docs/clearance-pack", json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "INVALID_ARGUMENT"
