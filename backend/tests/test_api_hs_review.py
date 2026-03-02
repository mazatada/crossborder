from app.models import HSClassification


def _create_classification(client, api_key_header, trace_id: str, product_id: str):
    payload = {
        "product": {
            "name": "Chocolate cookies",
            "category": "confectionery",
            "origin_country": "JP",
            "ingredients": [
                {"id": "ing_wheat_flour", "pct": 30.0},
                {"id": "ing_sugar", "pct": 25.0},
                {"id": "ing_cocoa", "pct": 15.0},
            ],
            "process": ["baking"],
        },
        "traceId": trace_id,
        "product_id": product_id,
    }
    resp = client.post("/v1/classify/hs", json=payload, headers=api_key_header)
    assert resp.status_code == 200


def test_hs_review_get_and_put(client, api_key_header, db_session):
    trace_id = "TEST-REVIEW-001"
    product_id = "prod_review_001"
    _create_classification(client, api_key_header, trace_id, product_id)

    record = db_session.query(HSClassification).filter_by(trace_id=trace_id).first()
    assert record is not None

    resp = client.get(f"/v1/hs-classifications/{record.id}", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["trace_id"] == trace_id
    assert data["final_hs_code"] == record.final_hs_code

    update_payload = {
        "final_source": "manual",
        "review_required": False,
        "review_comment": "Reviewed OK",
        "reviewed_by": "tester",
        "duty_rate_override": {
            "duty_rate": {
                "type": "ad_valorem",
                "ad_valorem_rate": 0.05,
                "specific": None,
                "currency": "USD",
                "basis_uom": None,
            },
            "additional_duties": [],
        },
    }
    resp = client.put(
        f"/v1/hs-classifications/{record.id}",
        json=update_payload,
        headers=api_key_header,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["final_source"] == "manual"
    assert data["review_comment"] == "Reviewed OK"
    assert data["reviewed_by"] == "tester"
    assert data["duty_rate_override"] is not None
    assert data["status"] in ["reviewed", "classified"]


def test_hs_review_not_found(client, api_key_header):
    resp = client.get("/v1/hs-classifications/999999", headers=api_key_header)
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"

    resp = client.put(
        "/v1/hs-classifications/999999",
        json={"review_comment": "nope"},
        headers=api_key_header,
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"


def test_hs_review_sets_reviewed_at(client, api_key_header, db_session):
    trace_id = "TEST-REVIEW-002"
    product_id = "prod_review_002"
    _create_classification(client, api_key_header, trace_id, product_id)

    record = db_session.query(HSClassification).filter_by(trace_id=trace_id).first()
    assert record is not None
    assert record.reviewed_at is None

    resp = client.put(
        f"/v1/hs-classifications/{record.id}",
        json={"review_comment": "Needs manual check", "reviewed_by": "qa"},
        headers=api_key_header,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["reviewed_at"] is not None
    assert data["status"] == "reviewed"


def test_hs_review_conflict_when_locked(client, api_key_header, db_session):
    trace_id = "TEST-REVIEW-LOCKED"
    product_id = "prod_review_locked"
    _create_classification(client, api_key_header, trace_id, product_id)

    record = db_session.query(HSClassification).filter_by(trace_id=trace_id).first()
    assert record is not None
    record.status = "locked"
    db_session.add(record)
    db_session.commit()

    resp = client.put(
        f"/v1/hs-classifications/{record.id}",
        json={"review_comment": "should fail"},
        headers=api_key_header,
    )
    assert resp.status_code == 409
    data = resp.get_json()
    assert data["error"]["class"] == "conflict"


def test_hs_classification_state_transition_defense():
    """Test that ORM @validates hook correctly blocks backward state transitions"""
    import pytest
    from app.models import HSClassification
    
    # Normal forward creation
    record = HSClassification(
        trace_id="test-val-1",
        product_name="test",
        hs_candidates=[],
        final_hs_code="1234.56",
        required_uom="kg",
        status="reviewed"
    )
    
    # Assert backward transition throws ValueError immediately on assignment
    with pytest.raises(ValueError, match="Invalid state transition from reviewed to pending"):
        record.status = "pending"
