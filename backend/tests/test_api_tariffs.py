import pytest


def test_get_tariff_ok(client, api_key_header):
    resp = client.get("/v1/tariffs/US/1905.90", headers=api_key_header)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["duty_rate"]["ad_valorem_rate"] == 0.05
    assert data["duty_rate"]["ad_valorem_pct"] == 5.0


def test_get_tariff_not_found(client, api_key_header):
    resp = client.get("/v1/tariffs/US/9999.99", headers=api_key_header)
    assert resp.status_code == 404


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
