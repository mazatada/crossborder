import pytest


@pytest.mark.unit
def test_translate_requires_input(client):
    response = client.post("/v1/translate/ingredients", json={})
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.unit
def test_translate_returns_terms_with_text(client):
    response = client.post("/v1/translate/ingredients", json={"text_ja": "小麦粉"})
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload["terms"], list)
    assert payload["terms"][0]["en"] == "wheat flour"


@pytest.mark.unit
def test_classify_rejects_empty_ingredients(client):
    response = client.post("/v1/classify/hs", json={"product": {"ingredients": []}})
    assert response.status_code == 422
    payload = response.get_json()
    assert payload["error"]["code"] == "UNPROCESSABLE"


@pytest.mark.unit
def test_classify_returns_candidates(client):
    response = client.post(
        "/v1/classify/hs",
        json={"product": {"ingredients": ["小麦粉", "砂糖"]}},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert "hs_candidates" in payload
    assert payload["hs_candidates"][0]["code"] == "1905.90"
