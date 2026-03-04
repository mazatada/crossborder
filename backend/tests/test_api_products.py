import pytest

def test_create_product(client, api_key_header):
    payload = {
        "title": "Test Macha",
        "description_en": "Japanese Matcha Powder",
        "origin_country": "JP",
        "is_food": True,
        "processing_state": "powder",
        "physical_form": "powder",
        "unit_weight_g": 50
    }
    res = client.post("/v1/products", json=payload, headers=api_key_header)
    assert res.status_code == 201
    data = res.get_json()
    assert data["title"] == "Test Macha"
    assert data["status"] == "draft"
    assert data["id"] is not None

def test_get_products(client, api_key_header):
    # First create
    client.post("/v1/products", json={"title": "Test 1"}, headers=api_key_header)
    
    res = client.get("/v1/products", headers=api_key_header)
    assert res.status_code == 200
    data = res.get_json()
    assert "data" in data
    assert len(data["data"]) > 0
    assert data["meta"]["total"] > 0

def test_update_product(client, api_key_header):
    res1 = client.post("/v1/products", json={"title": "To Update"}, headers=api_key_header)
    pid = res1.get_json()["id"]

    res2 = client.put(f"/v1/products/{pid}", json={"title": "Updated Title", "unit_weight_g": 100}, headers=api_key_header)
    assert res2.status_code == 200
    data = res2.get_json()
    assert data["title"] == "Updated Title"
    assert data["unit_weight_g"] == 100

def test_validate_product_success(client, api_key_header):
    payload = {
        "title": "Test Valid Food",
        "description_en": "Food item setup",
        "origin_country": "JP",
        "is_food": True,
        "processing_state": "processed",
        "physical_form": "solid",
        "unit_weight_g": 200,
        "shelf_life_days": 365,
        "animal_derived_flags": {}
    }
    res1 = client.post("/v1/products", json=payload, headers=api_key_header)
    pid = res1.get_json()["id"]

    res2 = client.post(f"/v1/products/{pid}/validate", headers=api_key_header)
    assert res2.status_code == 200
    data = res2.get_json()
    assert data["valid"] is True
    assert len(data["errors"]) == 0
    assert len(data["warnings"]) == 0

def test_validate_product_missing_fields(client, api_key_header):
    payload = {
        "title": "Test Invalid",
        "is_food": False
    }
    res1 = client.post("/v1/products", json=payload, headers=api_key_header)
    pid = res1.get_json()["id"]

    res2 = client.post(f"/v1/products/{pid}/validate", headers=api_key_header)
    assert res2.status_code == 200
    data = res2.get_json()
    assert data["valid"] is False
    assert len(data["errors"]) > 0

def test_validate_product_food_warnings(client, api_key_header):
    payload = {
        "title": "Test Valid Food with warnings",
        "description_en": "Food item setup",
        "origin_country": "JP",
        "is_food": True,
        "processing_state": "processed",
        "physical_form": "solid",
        "unit_weight_g": 200
    }
    res1 = client.post("/v1/products", json=payload, headers=api_key_header)
    pid = res1.get_json()["id"]

    res2 = client.post(f"/v1/products/{pid}/validate", headers=api_key_header)
    assert res2.status_code == 200
    data = res2.get_json()
    assert data["valid"] is True
    assert len(data["warnings"]) >= 2


def test_update_product_immutability(client, api_key_header):
    # Create product
    res1 = client.post("/v1/products", json={
        "title": "To Protect", 
        "description_en": "Desc",
        "origin_country": "JP",
        "processing_state": "processed",
        "physical_form": "solid",
        "unit_weight_g": 100,
        "is_food": False
    }, headers=api_key_header)
    pid = res1.get_json()["id"]

    # Change status to ready by validating
    res_val = client.post(f"/v1/products/{pid}/validate", headers=api_key_header)
    assert res_val.status_code == 200

    # Attempt to modify critical field
    res2 = client.put(f"/v1/products/{pid}", json={"is_food": True}, headers=api_key_header)
    assert res2.status_code == 409
    assert "Cannot modify critical field" in res2.get_json()["error"]
    
    # Attempt to modify non-critical field
    res3 = client.put(f"/v1/products/{pid}", json={"title": "Safe Update"}, headers=api_key_header)
    assert res3.status_code == 200
    assert res3.get_json()["title"] == "Safe Update"
