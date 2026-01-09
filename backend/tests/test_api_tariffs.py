import pytest


def test_get_tariff_ok(client, api_key_header):
    resp = client.get("/v1/tariffs/US/1905.90", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["duty_rate"]["ad_valorem_rate"] == 0.05
    assert data["duty_rate"]["ad_valorem_pct"] == 5.0


def test_get_tariff_with_origin_and_as_of(client, api_key_header):
    resp = client.get(
        "/v1/tariffs/US/1905.90?origin_country=JP&as_of=2025-12-06",
        headers=api_key_header,
    )
    assert resp.status_code == 200


def test_get_tariff_invalid_origin_country(client, api_key_header):
    resp = client.get(
        "/v1/tariffs/US/1905.90?origin_country=JPN",
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "invalid_format"


def test_get_tariff_invalid_as_of(client, api_key_header):
    resp = client.get(
        "/v1/tariffs/US/1905.90?as_of=20251206",
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "invalid_format"


def test_get_tariff_not_found(client, api_key_header):
    resp = client.get("/v1/tariffs/US/9999.99", headers=api_key_header)
    assert resp.status_code == 404
    data = resp.get_json()
    assert data["error"]["class"] == "not_found"


def test_calculate_tariff_ok(client, api_key_header):
    resp = client.post(
        "/v1/tariffs/calculate",
        json={
            "hs_code": "1905.90",
            "origin_country": "JP",
            "destination_country": "US",
            "customs_value": {"amount": 1000.0, "currency": "USD"},
        },
        headers=api_key_header,
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["duty"]["total_amount"] == 50.0


def test_get_tariff_invalid_hs_code(client, api_key_header):
    resp = client.get("/v1/tariffs/US/INVALID", headers=api_key_header)
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "invalid_format"


def test_calculate_tariff_invalid_hs_code(client, api_key_header):
    resp = client.post(
        "/v1/tariffs/calculate",
        json={
            "hs_code": "INVALID",
            "origin_country": "JP",
            "destination_country": "US",
            "customs_value": {"amount": 1000.0, "currency": "USD"},
        },
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "invalid_format"


def test_calculate_tariff_missing_required(client, api_key_header):
    resp = client.post(
        "/v1/tariffs/calculate",
        json={
            "origin_country": "JP",
            "destination_country": "US",
            "customs_value": {"amount": 1000.0, "currency": "USD"},
        },
        headers=api_key_header,
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"]["class"] == "missing_required"
