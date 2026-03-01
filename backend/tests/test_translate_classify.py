import pytest


@pytest.mark.unit
def test_translate_requires_input(client, api_key_header):
    response = client.post("/v1/translate/ingredients", json={}, headers=api_key_header)
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.unit
def test_translate_returns_terms_with_text(client, api_key_header):
    response = client.post(
        "/v1/translate/ingredients", json={"text_ja": "小麦粉"}, headers=api_key_header
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["terms"], list)
    assert payload["terms"][0]["en"] == "wheat flour"


@pytest.mark.unit
def test_classify_rejects_empty_ingredients(client, api_key_header):
    response = client.post(
        "/v1/classify/hs",
        json={"product": {"name": "Empty", "ingredients": []}},
        headers=api_key_header,
    )
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["violations"][0]["rule"] == "not_empty"


@pytest.mark.unit
def test_classify_returns_candidates(client, api_key_header):
    response = client.post(
        "/v1/classify/hs",
        json={
            "product": {
                "name": "Chocolate cookies",
                "category": "confectionery",
                "ingredients": [
                    {"id": "ing_wheat_flour", "pct": 30.0},
                    {"id": "ing_sugar", "pct": 25.0},
                ],
                "process": ["baking"],
                "origin_country": "JP",
            }
        },
        headers=api_key_header,
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "hs_candidates" in payload
    assert payload["hs_candidates"][0]["code"] == "1905.90"
