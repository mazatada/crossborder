import pytest
from datetime import datetime, timedelta

from app.db import db
from app.models import Job
from app.jobs import cli


@pytest.mark.integration
@pytest.mark.postgres
def test_scheduler_moves_stuck_running_to_retrying(monkeypatch):
    monkeypatch.setattr(cli, "VISIBILITY_TIMEOUT_SEC", 0)

    job = Job(
        type="pn_submit",
        status="running",
        attempts=1,
        next_run_at=None,
        payload_json={},
        result_json=None,
        trace_id="sched-trace",
        updated_at=datetime.utcnow() - timedelta(minutes=10),
    )
    db.session.add(job)
    db.session.commit()

    cli.scheduler_tick(db.session)

    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "retrying"
    assert refreshed.next_run_at is not None

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_worker_retries_on_handler_error(monkeypatch):
    record_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)

    def _raise_handler(payload, job_id=None, trace_id=None):
        raise ValueError("boom")

    monkeypatch.setattr(cli, "record_event", _record_event)
    monkeypatch.setattr(cli, "dispatch", _raise_handler)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={"traceId": "retry-trace"},
        trace_id="retry-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "retrying"
    assert refreshed.error is not None
    assert refreshed.error["class"] == "ValueError"

    assert record_calls[0]["event"] == "JOB_RETRYING"

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_worker_heartbeat_called_before_handler(monkeypatch):
    calls = []

    def _heartbeat(session, job):
        calls.append(("heartbeat", job.id))
        job.updated_at = datetime.utcnow()
        session.add(job)
        session.commit()

    def _handler(payload, job_id=None, trace_id=None):
        calls.append(("handler", job_id))
        return {"ok": True}

    monkeypatch.setattr(cli, "_heartbeat", _heartbeat)
    monkeypatch.setattr(cli, "dispatch", _handler)
    monkeypatch.setattr(cli, "record_event", lambda **kwargs: None)
    monkeypatch.setattr(cli, "_enqueue_webhook_jobs", lambda *a, **k: None)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={},
        trace_id="heartbeat-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "succeeded"
    assert calls[0][0] == "heartbeat"
    assert calls[1][0] == "handler"

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_requeue_and_cancel_paths(monkeypatch):
    record_calls = []
    monkeypatch.setattr(
        cli, "record_event", lambda **kwargs: record_calls.append(kwargs)
    )

    job = Job(
        type="pn_submit",
        status="failed",
        attempts=3,
        next_run_at=None,
        payload_json={},
        trace_id="requeue-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.requeue_job(job.id, session=db.session)
    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "queued"
    assert refreshed.attempts == 0
    assert record_calls[-1]["event"] == "JOB_REQUEUED"

    cli.cancel_job(job.id, session=db.session)
    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "canceled"
    assert record_calls[-1]["event"] == "JOB_CANCELED"

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_non_retriable_error_marks_failed(monkeypatch):
    record_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)

    def _handler(payload, job_id=None, trace_id=None):
        raise cli.NonRetriableError("fatal")

    monkeypatch.setattr(cli, "dispatch", _handler)
    monkeypatch.setattr(cli, "record_event", _record_event)
    monkeypatch.setattr(cli, "_enqueue_webhook_jobs", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_heartbeat", lambda *a, **k: None)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={},
        trace_id="nonret-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "failed"
    assert refreshed.error["class"] == "NonRetriableError"
    assert record_calls[-1]["event"] == "JOB_FAILED"
    assert record_calls[-1].get("retriable") is False

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_webhook_failure_is_recorded_but_job_remains_succeeded(monkeypatch):
    record_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)
        return True

    def _handler(payload, job_id=None, trace_id=None):
        return {"ok": True}

    monkeypatch.setattr(cli, "dispatch", _handler)
    monkeypatch.setattr("app.jobs.cli.record_event", _record_event, raising=False)
    monkeypatch.setattr("app.jobs.cli._enqueue_webhook_jobs", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(cli, "_heartbeat", lambda *a, **k: None)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={},
        trace_id="webhook-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    refreshed = db.session.get(Job, job.id)
    # Outbox化により、ジョブ自体は成功する（webhook送信は非同期ジョブへ）
    assert refreshed.status == "succeeded"
    assert any(c["event"] == "JOB_SUCCEEDED" for c in record_calls)

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_non_retriable_raised_from_handlers(monkeypatch):
    record_calls = []
    monkeypatch.setattr(
        cli, "record_event", lambda **kwargs: record_calls.append(kwargs)
    )
    monkeypatch.setattr(cli, "_enqueue_webhook_jobs", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_heartbeat", lambda *a, **k: None)

    # モックハンドラの登録
    def _mock_handler_raising(payload, job_id=None, trace_id=None):
        raise cli.NonRetriableError("test non-retriable")

    # cli.REGISTRY を確実にパッチするために sys.modules から取得
    import sys
    cli_module = sys.modules["app.jobs.cli"]
    monkeypatch.setitem(cli_module.REGISTRY, "clearance_pack", _mock_handler_raising)
    monkeypatch.setitem(cli_module.REGISTRY, "pn_submit", _mock_handler_raising)

    job1 = Job(
        type="clearance_pack",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={},
        trace_id="nr-clearance",
    )
    job2 = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={
            "traceId": "nr-pn",
            "product": {},
            "logistics": {},
            "consignee": {},
        },
        trace_id="nr-pn",
    )
    db.session.add_all([job1, job2])
    db.session.commit()

    cli.worker_once(db.session)
    cli.worker_once(db.session)

    refreshed1 = db.session.get(Job, job1.id)
    refreshed2 = db.session.get(Job, job2.id)
    assert refreshed1.status == "failed"
    assert refreshed1.error["class"] == "NonRetriableError"
    assert refreshed2.status == "failed"
    assert refreshed2.error["class"] == "NonRetriableError"

    db.session.delete(refreshed1)
    db.session.delete(refreshed2)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_webhook_failure_enqueues_retry_job(monkeypatch):
    """Outbox方式ではwebhook_dispatchジョブが非同期で作成されるため、
    ジョブ完了後にwebhook_dispatchタイプのジョブが生成されることを確認する。"""
    record_calls = []
    enqueue_calls = []

    def _record_event(**kwargs):
        record_calls.append(kwargs)

    def _handler(payload, job_id=None, trace_id=None):
        return {"ok": True}

    def _mock_enqueue(session, job, result):
        enqueue_calls.append({"job_id": job.id, "type": job.type})

    monkeypatch.setattr(cli, "dispatch", _handler)
    monkeypatch.setattr(cli, "record_event", _record_event)
    monkeypatch.setattr(cli, "_enqueue_webhook_jobs", _mock_enqueue)
    monkeypatch.setattr(cli, "_heartbeat", lambda *a, **k: None)

    job = Job(
        type="pn_submit",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={},
        trace_id="webhook-retry-trace",
    )
    db.session.add(job)
    db.session.commit()

    cli.worker_once(db.session)

    # _enqueue_webhook_jobs が呼ばれたことを確認
    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["type"] == "pn_submit"

    refreshed = db.session.get(Job, job.id)
    assert refreshed.status == "succeeded"

    db.session.delete(refreshed)
    db.session.commit()


@pytest.mark.integration
@pytest.mark.postgres
def test_webhook_retry_respects_max_attempts(monkeypatch):
    """webhook_retryジョブがmax_attempts超過時にDLQへ退避されることを確認"""
    monkeypatch.setattr("app.jobs.cli._heartbeat", lambda *a, **k: None)
    monkeypatch.setattr("app.jobs.cli.record_event", lambda **kw: True, raising=False)
    monkeypatch.setattr("app.jobs.cli._enqueue_webhook_jobs", lambda *a, **k: None, raising=False)
    monkeypatch.setattr(
        "app.jobs.handlers.webhook_retry.post_event",
        lambda *a, **k: {"status": 503},
        raising=False,
    )
    # Config monkeypatch to fail after 1 attempt
    import sys
    cli_module = sys.modules["app.jobs.cli"]
    monkeypatch.setattr(cli_module, "MAX_ATTEMPTS", 1)

    retry_job = Job(
        type="webhook_retry",
        status="queued",
        attempts=0,
        next_run_at=datetime.utcnow() - timedelta(seconds=1),
        payload_json={
            "event_type": "PN_SUBMITTED",
            "payload": {},
            "trace_id": "webhook-retry-max",
            "retry_max_attempts": 1,
            "retry_base_sec": 1,
        },
        trace_id="webhook-retry-max",
    )
    db.session.add(retry_job)
    db.session.commit()

    # first attempt -> retrying (attempts=1), second -> failed (attempts>=max)
    cli.worker_once(db.session)
    
    # データをリフレッシュして next_run_at を過去に戻す (そうしないと拾われない)
    refreshed_retry = db.session.get(Job, retry_job.id)
    refreshed_retry.next_run_at = datetime.utcnow() - timedelta(seconds=1)
    db.session.add(refreshed_retry)
    db.session.commit()
    
    cli.worker_once(db.session)

    refreshed_retry = db.session.get(Job, retry_job.id)
    assert refreshed_retry.status == "failed"
    assert refreshed_retry.error["class"] == "NonRetriableError"

    db.session.delete(retry_job)
    db.session.commit()
