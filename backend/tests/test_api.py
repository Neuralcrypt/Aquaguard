import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["room"] == "ROOM-101"

def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_reject_negative_reading(client):
    response = client.post("/api/readings", json={"room_id":"ROOM-101", "sensor_id":"SENSOR-101", "flow_rate_lpm":-1, "interval_volume_litres":1})
    assert response.status_code == 422

def test_settings_have_three_seasons(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    assert {row["season"] for row in response.json()} == {"Summer", "Monsoon", "Winter"}
