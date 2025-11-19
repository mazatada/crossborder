import pytest


@pytest.mark.unit
def test_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert "ts" in data


@pytest.mark.unit
def test_version(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "test-version")
    monkeypatch.setenv("COMMIT", "abc123")

    response = client.get("/v1/version")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == "test-version"
    assert data["commit"] == "abc123"
