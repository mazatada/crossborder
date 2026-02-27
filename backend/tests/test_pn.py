import pytest

from app.db import db
from app.models import Job




@pytest.mark.integration
def test_prior_notice_queues_job_and_records_event(client, monkeypatch, api_key_header):
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
    response = client.post("/v1/fda/prior-notice", json=payload, headers=api_key_header)
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
def test_prior_notice_missing_required_fields(client, api_key_header):
    response = client.post("/v1/fda/prior-notice", json={}, headers=api_key_header)
    assert response.status_code == 400
    body = response.get_json()
    assert body["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.integration
@pytest.mark.postgres
def test_worker_processes_prior_notice_job(monkeypatch):
    from datetime import datetime, timedelta
    from app.models import Job
    from app.jobs import cli

    record_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)

    monkeypatch.setattr("app.jobs.cli.record_event", _record_event)
    monkeypatch.setattr("app.jobs.cli._enqueue_webhook_jobs", lambda *a, **k: None)

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
        trace_id="test-pn-job",
    )

    import sys
    cli_module = sys.modules["app.jobs.cli"]
    
    # モックハンドラの登録 (成功させる + 期待値を返す)
    monkeypatch.setitem(
        cli_module.REGISTRY,
        "pn_submit",
        lambda *args, **k: {"ok": True, "receipt_media_id": "dev:pn-receipt"},
    )

    # 1. ジョブ作成
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    job = db.session.get(Job, job.id)
    assert job.status == "succeeded"
    assert job.result_json["receipt_media_id"] == "dev:pn-receipt"

    # Outbox化により直接webhookは呼ばれない。
    # record_eventでJOB_SUCCEEDED が記録されていることを確認
    assert any(c["event"] == "JOB_SUCCEEDED" for c in record_calls)

    db.session.delete(job)
    db.session.commit()
