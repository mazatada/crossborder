import pytest
from app.jobs.handlers import clearance_pack, pn_submit

def test_translate_mock(client):
    """Test translation API with mock trigger"""
    resp = client.post("/v1/translate/ingredients", json={
        "text_ja": "MOCK_TEST",
        "traceId": "TEST-TRACE-001"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert "terms" in data
    assert len(data["terms"]) > 0
    assert data["terms"][0]["en"] == "wheat flour"

def test_classify_rule_engine(client):
    """Test HS classification rule engine"""
    # Case 1: Cookie (1905.90)
    resp = client.post("/v1/classify/hs", json={
        "product": {
            "name": "Delicious Cookie",
            "ingredients": [{"en": "wheat flour"}, {"en": "sugar"}]
        },
        "traceId": "TEST-TRACE-002"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["hs_candidates"][0]["code"] == "1905.90"
    assert data["hs_candidates"][0]["confidence"] > 0.8

    # Case 2: Green Tea (0902.10)
    resp = client.post("/v1/classify/hs", json={
        "product": {
            "name": "Premium Green Tea",
            "ingredients": [{"en": "green tea leaves"}]
        }
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["hs_candidates"][0]["code"] == "0902.10"

def test_clearance_pack_handler():
    """Unit test for PDF generation handler"""
    payload = {
        "required_uom": "kg",
        "invoice_uom": "kg"
    }
    result = clearance_pack.handle(payload, job_id=1, trace_id="TEST-TRACE-003")
    
    assert "artifacts" in result
    assert len(result["artifacts"]) == 2
    
    # Check if PDF size is reasonable (not empty)
    invoice = next(a for a in result["artifacts"] if a["type"] == "commercial_invoice")
    assert invoice["size"] > 100  # PDF header alone is ~100 bytes
    assert invoice["media_id"].startswith("doc:ci:")

def test_pn_submit_handler():
    """Unit test for PN submission handler"""
    payload = {
        "traceId": "TEST-TRACE-004",
        "product": {"name": "Cookie"},
        "logistics": {"mode": "AIR"},
        "importer": {"name": "US Importer"},
        "consignee": {"name": "US Consignee"}
    }
    result = pn_submit.handle(payload, job_id=2, trace_id="TEST-TRACE-004")
    
    assert result["submitted"] is True
    assert "confirmation_number" in result
    assert result["trace_id"] == "TEST-TRACE-004"

def test_docs_api_creates_job(client):
    """Test that /docs/clearance-pack creates a job"""
    resp = client.post("/v1/docs/clearance-pack", json={
        "traceId": "TEST-TRACE-005",
        "hs_code": "1905.90",
        "required_uom": "kg",
        "invoice_uom": "kg"
    })
    assert resp.status_code == 202
    data = resp.get_json()
    assert "job_id" in data
    assert data["status"] == "queued"

def test_pn_api_creates_job(client):
    """Test that /fda/prior-notice creates a job"""
    resp = client.post("/v1/fda/prior-notice", json={
        "traceId": "TEST-TRACE-006",
        "product": {},
        "logistics": {},
        "importer": {},
        "consignee": {}
    })
    assert resp.status_code == 202
    data = resp.get_json()
    assert "job_id" in data
