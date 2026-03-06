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


def test_compliance_view(client, api_key_header, db_session):
    trace_id = "TEST-COMPLIANCE-001"
    product_id = "prod_comp_001"
    _create_classification(client, api_key_header, trace_id, product_id)

    record = db_session.query(HSClassification).filter_by(trace_id=trace_id).first()
    assert record is not None

    # create docs job
    resp = client.post(
        "/v1/docs/clearance-pack",
        json={
            "traceId": trace_id,
            "hs_code": record.final_hs_code,
            "required_uom": record.required_uom,
            "invoice_uom": record.required_uom,
        },
        headers=api_key_header,
    )
    assert resp.status_code == 202

    # create pn job
    resp = client.post(
        "/v1/fda/prior-notice",
        json={
            "traceId": trace_id,
            "product": {
                "name": "Chocolate cookies",
                "description": "test",
                "hs_code": record.final_hs_code,
                "origin_country": "JP",
            },
            "logistics": {
                "mode": "AIR",
                "carrier": "TEST",
                "port_of_entry": "JFK",
                "arrival_date": "2025-12-06",
            },
            "importer": {"name": "Importer"},
            "consignee": {"name": "Consignee"},
        },
        headers=api_key_header,
    )
    assert resp.status_code == 202

    resp = client.get(f"/v1/products/{product_id}/compliance", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["product_id"] == product_id
    assert data["trace_id"] == trace_id
    assert data["hs_classification"]["final_hs_code"] == record.final_hs_code
    assert data["docs"] is not None


def test_compliance_not_found(client, api_key_header):
    resp = client.get("/v1/products/unknown/compliance", headers=api_key_header)
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"


def test_compliance_without_jobs(client, api_key_header, db_session):
    trace_id = "TEST-COMPLIANCE-002"
    product_id = "prod_comp_002"
    _create_classification(client, api_key_header, trace_id, product_id)

    record = db_session.query(HSClassification).filter_by(trace_id=trace_id).first()
    assert record is not None

    resp = client.get(f"/v1/products/{product_id}/compliance", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["product_id"] == product_id
    assert data["trace_id"] == trace_id
    assert data["docs"] is None


def test_evaluate_compliance_missing_fields(client, api_key_header):
    res = client.post(
        "/v1/evaluate", json={"product_id": "123"}, headers=api_key_header
    )
    assert res.status_code == 400


def test_evaluate_compliance_us_food(client, api_key_header, db_session):
    from app.models import Product

    p = Product(title="US Food", is_food=True, status="ready")
    db_session.add(p)
    db_session.commit()

    res = client.post(
        "/v1/evaluate",
        json={
            "product_id": p.id,
            "destination_country": "US",
            "shipping_mode": "postal",
            "incoterm": "DDU",
        },
        headers=api_key_header,
    )

    assert res.status_code == 200
    data = res.get_json()
    assert data["allowed"] is True
    assert "fda_product_code" in data["required_codes"]
    assert "fda_facility_registration_number" in data["required_codes"]
    assert any("FDA Prior Notice" in note for note in data["notes"])
    assert any("Postal" in note for note in data["notes"])


def test_evaluate_compliance_ddp_postal_block(client, api_key_header, db_session):
    from app.models import Product

    p = Product(title="Regular item", is_food=False, status="ready")
    db_session.add(p)
    db_session.commit()

    res = client.post(
        "/v1/evaluate",
        json={
            "product_id": p.id,
            "destination_country": "JP",
            "shipping_mode": "postal",
            "incoterm": "DDP",
        },
        headers=api_key_header,
    )

    assert res.status_code == 200
    data = res.get_json()
    assert data["allowed"] is False
    assert len(data["block_reasons"]) > 0


def test_evaluate_compliance_validation_errors(client, api_key_header, db_session):
    from app.models import Product

    p = Product(title="Test", is_food=False, status="ready")
    db_session.add(p)
    db_session.commit()

    # Invalid country length
    res1 = client.post(
        "/v1/evaluate",
        json={"product_id": p.id, "destination_country": "USA"},
        headers=api_key_header,
    )
    assert res1.status_code == 400

    # Invalid country characters
    res2 = client.post(
        "/v1/evaluate",
        json={"product_id": p.id, "destination_country": "J1"},
        headers=api_key_header,
    )
    assert res2.status_code == 400

    # Invalid shipping mode
    res3 = client.post(
        "/v1/evaluate",
        json={
            "product_id": p.id,
            "destination_country": "JP",
            "shipping_mode": "postel",
        },
        headers=api_key_header,
    )
    assert res3.status_code == 400
