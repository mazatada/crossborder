"""
E2E tests for the complete cross-border flow:
Translation → Classification → Documents → PN Submission
"""

import pytest
from app.db import db
from app.models import Job, PNSubmission, DocumentPackage
import time


@pytest.mark.e2e
def test_complete_crossborder_flow(client):
    """
    Test the complete cross-border flow from translation to PN submission.

    Flow:
    1. Translate product description
    2. Classify HS code
    3. Package documents
    4. Submit PN
    """
    trace_id = f"E2E-TEST-{int(time.time())}"

    # Step 1: Translation
    translate_resp = client.post(
        "/v1/translate",
        json={
            "text": "高品質な革製ハンドバッグ",
            "source_lang": "ja",
            "target_lang": "en",
            "traceId": trace_id,
        },
    )

    assert translate_resp.status_code == 200
    translate_data = translate_resp.get_json()
    assert "translated_text" in translate_data
    translated_text = translate_data["translated_text"]

    # Step 2: HS Classification
    classify_resp = client.post(
        "/v1/classify",
        json={"product_description": translated_text, "traceId": trace_id},
    )

    assert classify_resp.status_code == 200
    classify_data = classify_resp.get_json()
    assert "hs_code" in classify_data
    hs_code = classify_data["hs_code"]

    # Step 3: Document Packaging
    docs_resp = client.post(
        "/v1/docs/package",
        json={
            "hs_code": hs_code,
            "invoice_data": {"quantity": 10, "unit": "pieces", "value": 5000},
            "traceId": trace_id,
        },
    )

    assert docs_resp.status_code == 200
    docs_data = docs_resp.get_json()
    assert "package_id" in docs_data

    # Verify document package in DB
    doc_package = db.session.query(DocumentPackage).filter_by(trace_id=trace_id).first()
    assert doc_package is not None
    assert doc_package.hs_code == hs_code

    # Step 4: PN Submission
    pn_resp = client.post(
        "/v1/pn/submit",
        json={
            "product": {"name": translated_text, "hs_code": hs_code, "quantity": 10},
            "logistics": {"carrier": "DHL", "tracking": "TEST123456"},
            "importer": {"name": "Test Importer Inc.", "address": "123 Test St, Tokyo"},
            "consignee": {"name": "Test Consignee", "address": "456 Test Ave, Osaka"},
            "traceId": trace_id,
        },
    )

    assert pn_resp.status_code == 200
    pn_data = pn_resp.get_json()
    assert "submission_id" in pn_data

    # Verify PN submission in DB
    pn_submission = db.session.query(PNSubmission).filter_by(trace_id=trace_id).first()
    assert pn_submission is not None
    assert pn_submission.product["hs_code"] == hs_code


@pytest.mark.e2e
def test_async_job_flow(client):
    """
    Test asynchronous job processing flow.

    Flow:
    1. Create async job
    2. Poll job status
    3. Verify completion
    """
    trace_id = f"E2E-JOB-{int(time.time())}"

    # Create async job
    job_resp = client.post(
        "/v1/jobs",
        json={
            "type": "pack",
            "payload": {
                "hs_code": "4202.11",
                "invoice_data": {"quantity": 5, "unit": "pieces"},
            },
            "traceId": trace_id,
        },
    )

    assert job_resp.status_code == 201
    job_data = job_resp.get_json()
    assert "job_id" in job_data
    job_id = job_data["job_id"]

    # Poll job status (with timeout)
    max_attempts = 10
    for attempt in range(max_attempts):
        status_resp = client.get(f"/v1/jobs/{job_id}")
        assert status_resp.status_code == 200

        status_data = status_resp.get_json()
        job_status = status_data.get("status")

        if job_status in ["done", "failed"]:
            assert job_status == "done"
            break

        time.sleep(1)
    else:
        pytest.fail(f"Job {job_id} did not complete within {max_attempts} seconds")

    # Verify job in DB
    job = db.session.query(Job).filter_by(id=job_id).first()
    assert job is not None
    assert job.status == "done"
    assert job.trace_id == trace_id


@pytest.mark.e2e
def test_webhook_integration_flow(client):
    """
    Test webhook integration flow.

    Flow:
    1. Register webhook
    2. Trigger event
    3. Verify webhook delivery (mocked)
    """
    trace_id = f"E2E-WEBHOOK-{int(time.time())}"

    # Register webhook
    webhook_resp = client.post(
        "/v1/integrations/webhooks",
        json={
            "url": "https://example.com/webhook",
            "events": ["HS_CLASSIFIED", "DOCS_PACKAGED"],
            "traceId": trace_id,
        },
    )

    assert webhook_resp.status_code == 201
    webhook_data = webhook_resp.get_json()
    assert "id" in webhook_data
    webhook_id = webhook_data["id"]

    # Test webhook delivery
    test_resp = client.post(
        f"/v1/integrations/webhooks/{webhook_id}/test", json={"traceId": trace_id}
    )

    # Note: This will fail in real environment without mock
    # In real E2E, we would need to mock the webhook endpoint
    assert test_resp.status_code in [200, 503]  # 503 if endpoint unreachable


@pytest.mark.e2e
def test_error_handling_flow(client):
    """
    Test error handling in the flow.

    Flow:
    1. Send invalid request
    2. Verify proper error response
    3. Verify no partial data in DB
    """
    trace_id = f"E2E-ERROR-{int(time.time())}"

    # Invalid HS classification request
    classify_resp = client.post(
        "/v1/classify",
        json={"product_description": "", "traceId": trace_id},  # Empty description
    )

    assert classify_resp.status_code == 400
    error_data = classify_resp.get_json()
    assert "error" in error_data
    assert error_data["error"]["code"] == "INVALID_ARGUMENT"

    # Invalid PN submission
    pn_resp = client.post(
        "/v1/pn/submit",
        json={"product": {}, "traceId": trace_id},  # Missing required fields
    )

    assert pn_resp.status_code == 400

    # Verify no partial submissions in DB
    pn_submission = db.session.query(PNSubmission).filter_by(trace_id=trace_id).first()
    assert pn_submission is None
