import json


def test_list_hs_rules(client, api_key_header):
    resp = client.get("/v1/hs-rules", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "items" in data
    assert "has_more" in data
    assert "next_cursor" in data


def test_create_update_delete_hs_rule(client, api_key_header):
    create_payload = {
        "name": "Test rule",
        "description": "test rule",
        "priority": 1,
        "scope": "food",
        "condition_dsl": json.dumps({"all": [{"always": {}}]}),
        "effect": {"hs_code": "1905.90", "weight": 0.9, "tags": ["test"]},
        "status": "draft",
    }
    resp = client.post("/v1/hs-rules", json=create_payload, headers=api_key_header)
    assert resp.status_code == 201
    data = resp.get_json()
    rule_id = data["id"]
    assert data["version"] == 1

    update_payload = {
        "condition_dsl": json.dumps({"all": [{"always": {}}]}),
        "priority": 2,
    }
    resp = client.put(
        f"/v1/hs-rules/{rule_id}", json=update_payload, headers=api_key_header
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["version"] == 2
    assert data["priority"] == 2

    resp = client.delete(f"/v1/hs-rules/{rule_id}", headers=api_key_header)
    assert resp.status_code == 204

    resp = client.get(f"/v1/hs-rules/{rule_id}", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "inactive"


def test_hs_rules_not_found(client, api_key_header):
    resp = client.get("/v1/hs-rules/does-not-exist", headers=api_key_header)
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"

    resp = client.put(
        "/v1/hs-rules/does-not-exist",
        json={"priority": 1},
        headers=api_key_header,
    )
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"

    resp = client.delete("/v1/hs-rules/does-not-exist", headers=api_key_header)
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"


def test_hs_rules_create_missing_fields(client, api_key_header):
    resp = client.post("/v1/hs-rules", json={}, headers=api_key_header)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "missing_required"
    assert data["error"]["field"] == "name"

    resp = client.post(
        "/v1/hs-rules",
        json={"name": "Test"},
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "missing_required"
    assert data["error"]["field"] == "condition_dsl"

    resp = client.post(
        "/v1/hs-rules",
        json={"name": "Test", "condition_dsl": "{}"},
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "missing_required"
    assert data["error"]["field"] == "effect.hs_code"


def test_hs_rules_create_invalid_dsl(client, api_key_header):
    create_payload = {
        "name": "Bad rule",
        "description": "bad rule",
        "priority": 1,
        "scope": "food",
        "condition_dsl": json.dumps({"all": [{"unknown_pred": {}}]}),
        "effect": {"hs_code": "1905.90", "weight": 0.9, "tags": ["test"]},
        "status": "draft",
    }
    resp = client.post("/v1/hs-rules", json=create_payload, headers=api_key_header)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "rule_dsl_error"


def test_hs_rules_update_invalid_dsl(client, api_key_header):
    create_payload = {
        "name": "Update rule",
        "description": "test rule",
        "priority": 1,
        "scope": "food",
        "condition_dsl": json.dumps({"all": [{"always": {}}]}),
        "effect": {"hs_code": "1905.90", "weight": 0.9, "tags": ["test"]},
        "status": "draft",
    }
    resp = client.post("/v1/hs-rules", json=create_payload, headers=api_key_header)
    assert resp.status_code == 201
    rule_id = resp.get_json()["id"]

    update_payload = {
        "condition_dsl": json.dumps({"any": [{"unknown_pred": {}}]}),
    }
    resp = client.put(
        f"/v1/hs-rules/{rule_id}", json=update_payload, headers=api_key_header
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "rule_dsl_error"


def test_hs_rules_update_missing_dsl(client, api_key_header):
    create_payload = {
        "name": "Update rule missing dsl",
        "description": "test rule",
        "priority": 1,
        "scope": "food",
        "condition_dsl": json.dumps({"all": [{"always": {}}]}),
        "effect": {"hs_code": "1905.90", "weight": 0.9, "tags": ["test"]},
        "status": "draft",
    }
    resp = client.post("/v1/hs-rules", json=create_payload, headers=api_key_header)
    assert resp.status_code == 201
    rule_id = resp.get_json()["id"]

    resp = client.put(
        f"/v1/hs-rules/{rule_id}",
        json={"condition_dsl": ""},
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "missing_required"
    assert data["error"]["field"] == "condition_dsl"


def test_hs_rules_test_endpoint(client, api_key_header):
    payload = {
        "rule": {
            "name": "Test rule",
            "condition_dsl": json.dumps({"all": [{"always": {}}]}),
            "effect": {"hs_code": "1905.90", "weight": 0.8},
        },
        "product_sample": {
            "name": "Sample",
            "ingredients": [{"name": "wheat flour", "pct": 40.0}],
            "category": "food",
        },
    }
    resp = client.post("/v1/hs-rules:test", json=payload, headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["matched"] is True
    assert data["effect_preview"]["hs_code"] == "1905.90"


def test_hs_rules_test_invalid_dsl(client, api_key_header):
    payload = {
        "rule": {
            "name": "Bad rule",
            "condition_dsl": "{invalid-json",
            "effect": {"hs_code": "1905.90", "weight": 0.8},
        },
        "product_sample": {"name": "Sample"},
    }
    resp = client.post("/v1/hs-rules:test", json=payload, headers=api_key_header)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "rule_dsl_error"
