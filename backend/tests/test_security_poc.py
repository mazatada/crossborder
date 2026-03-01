import pytest
import time
from app.db import db


@pytest.mark.security
def test_huge_payload_dos(client, api_key_header):
    """
    Test resilience against huge payloads (DoS attempt).
    Sends a product with 10,000 ingredients.
    """
    trace_id = "SEC-DOS-TEST"
    huge_ingredients = [{"name": f"ing_{i}", "percentage": 0.01} for i in range(10000)]

    start_time = time.time()
    resp = client.post(
        "/v1/classify/hs",
        json={
            "product": {
                "name": "Huge Product",
                "ingredients": huge_ingredients,
                "traceId": trace_id,
            }
        },
        headers=api_key_header,
    )
    duration = time.time() - start_time
    print(f"\n[Security] Huge payload (10k items) processed in {duration:.2f}s")

    # Expectation: Should be rejected with 400 due to resource exhaustion limit (Max 100)
    assert resp.status_code == 400
    err = resp.get_json()
    assert err["error"]["class"] == "resource_exhausted"


@pytest.mark.security
def test_trace_id_injection(client, api_key_header):
    """
    Test handling of malicious trace_id (Stored XSS / Log Injection).
    """
    # XSS payload in trace_id
    malicious_trace_id = '"><script>alert("XSS")</script>'

    resp = client.post(
        "/v1/classify/hs",
        json={
            "product": {
                "name": "Injection Test Product",
            },
            "traceId": malicious_trace_id,  # Inject here (Root level)
        },
        headers=api_key_header,
    )

    # Expectation: Should be rejected due to strict regex validation for trace_id
    assert resp.status_code == 400
    err = resp.get_json()
    assert err["error"]["message"] == "Invalid trace_id format"

    # Verify NOT stored
    from app.models import HSClassification

    record = (
        db.session.query(HSClassification)
        .filter_by(product_name="Injection Test Product")
        .first()
    )
    assert record is None
