import pytest
from app.models import HSClassification, Product

def test_list_hs_reviews(client, api_key_header, app, db_session):
    # Setup some classifications
    record1 = HSClassification(trace_id="tr1", product_name="test1", hs_candidates=[], final_hs_code="", required_uom="kg", status="pending")
    record2 = HSClassification(trace_id="tr2", product_name="test2", hs_candidates=[], final_hs_code="1234.56", required_uom="kg", status="reviewed")
    db_session.add_all([record1, record2])
    db_session.commit()

    res = client.get("/v1/reviews/hs?status=pending", headers=api_key_header)
    assert res.status_code == 200
    data = res.get_json()
    assert len(data["data"]) == 1
    assert data["data"][0]["status"] == "pending"

def test_assign_hs_review(client, api_key_header, db_session):
    record = HSClassification(trace_id="tr3", product_name="test3", hs_candidates=[], final_hs_code="", required_uom="kg", status="pending")
    db_session.add(record)
    db_session.commit()

    res = client.post(f"/v1/reviews/hs/{record.id}/assign", json={"operator_id": "op1"}, headers=api_key_header)
    assert res.status_code == 200
    data = res.get_json()
    assert data["reviewed_by"] == "op1"
    # The status_for_record will evaluate it as in_progress because final_hs_code is missing.
    assert data["status"] == "in_progress"

def test_finalize_hs_review(client, api_key_header, db_session):
    product = Product(title="Test Product for Finalize", description_en="desc", origin_country="JP", is_food=False, status="draft")
    db_session.add(product)
    db_session.commit()

    record = HSClassification(trace_id="tr4", product_id=product.id, product_name="test4", hs_candidates=[], final_hs_code="", required_uom="kg", status="pending")
    db_session.add(record)
    db_session.commit()

    res = client.post(f"/v1/reviews/hs/{record.id}/finalize", json={"final_hs_code": "9999.99"}, headers=api_key_header)
    assert res.status_code == 200
    data = res.get_json()
    assert data["final_hs_code"] == "9999.99"
    assert data["status"] == "reviewed"

    # Verify Product is updated
    db_session.refresh(product)
    assert product.hs_base6 == "9999.99"
    assert product.active_classification_id == record.id

def test_lock_hs_review(client, api_key_header, db_session):
    record = HSClassification(trace_id="tr5", product_name="test5", hs_candidates=[], final_hs_code="", required_uom="kg", status="reviewed")
    db_session.add(record)
    db_session.commit()

    res = client.post(f"/v1/reviews/hs/{record.id}/lock", headers=api_key_header)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "locked"

    # Subsequent assign/finalize should fail due to locked status
    res2 = client.post(f"/v1/reviews/hs/{record.id}/assign", json={"operator_id": "op2"}, headers=api_key_header)
    assert res2.status_code == 409
