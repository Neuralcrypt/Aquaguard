
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.auth import Hostel, User
from app.core.security import hash_password


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:

        # Create a test warden for the initial Bamashah Hostel.
        db = SessionLocal()

        try:
            hostel = (
                db.query(Hostel)
                .filter(Hostel.is_initial.is_(True))
                .first()
            )

            assert hostel is not None

            warden = (
                db.query(User)
                .filter(User.username == "test_warden")
                .first()
            )

            if warden is None:
                warden = User(
                    username="test_warden",
                    password_hash=hash_password("testpass123"),
                    role="warden",
                    hostel_id=hostel.id,
                    is_active=True,
                    token_version=0,
                )
                db.add(warden)
            else:
                warden.password_hash = hash_password("testpass123")
                warden.hostel_id = hostel.id
                warden.is_active = True
                warden.token_version += 1

            db.commit()

        finally:
            db.close()

        # Log in as the test warden.
        login_response = test_client.post(
            "/api/auth/login",
            json={
                "username": "test_warden",
                "password": "testpass123",
            },
        )

        assert login_response.status_code == 200

        token = login_response.json()["access_token"]
        test_client.headers.update(
            {"Authorization": f"Bearer {token}"}
        )

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
    response = client.post(
        "/api/readings",
        headers={
            "X-Device-Key": "test-only-device-key-for-pytest"
        },
        json={
            "room_id": "ROOM-101",
            "sensor_id": "SENSOR-101",
            "flow_rate_lpm": -1,
            "interval_volume_litres": 1,
        },
    )

    assert response.status_code == 422


def test_settings_have_three_seasons(client):
    response = client.get("/api/settings")

    assert response.status_code == 200
    assert {
        row["season"] for row in response.json()
    } == {"Summer", "Monsoon", "Winter"}
