from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "platform-owner",
    "password": "correct horse battery staple",
    "settings": {
        "language": "sv",
        "region": "SE",
        "base_currency": "SEK",
        "timezone": "Europe/Stockholm",
        "date_format": "YYYY-MM-DD",
        "number_format": "space-comma",
        "week_start": "monday",
    },
}


def test_health_and_setup_status_expose_persistent_test_identity(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    status = client.get("/api/v1/setup/status")

    assert health.status_code == 200
    assert health.json()["environment"] == "test"
    assert health.json()["database"] == "reachable"
    assert status.status_code == 200
    assert status.json()["setup_required"] is True
    assert status.json()["data_plane_id"] == health.json()["data_plane_id"]


def test_setup_locks_and_creates_environment_scoped_session(
    client: TestClient, settings: Settings
) -> None:
    response = client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["username"] == "platform-owner"
    assert response.json()["environment"] == "test"
    assert client.cookies.get(settings.session_cookie_name)
    assert client.cookies.get(settings.csrf_cookie_name)

    locked = client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "setup_locked"

    current = client.get("/api/v1/auth/session")
    assert current.status_code == 200
    assert current.json()["settings"]["timezone"] == "Europe/Stockholm"


def test_invalid_credentials_and_csrf_are_rejected(client: TestClient, settings: Settings) -> None:
    client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    client.cookies.clear()

    invalid_login = client.post(
        "/api/v1/auth/login",
        json={"username": "platform-owner", "password": "not-the-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["error"]["code"] == "invalid_credentials"

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "platform-owner", "password": SETUP_PAYLOAD["password"]},
    )
    assert login.status_code == 200

    rejected = client.patch("/api/v1/settings", json={"language": "en"})
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "csrf_failed"

    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    updated = client.patch(
        "/api/v1/settings",
        json={"language": "en"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert updated.status_code == 200
    assert updated.json()["language"] == "en"


def test_demo_reset_requires_confirmation_and_resets_only_test_configuration(
    client: TestClient, settings: Settings
) -> None:
    setup = client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert setup.status_code == 201
    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    headers = {"X-CSRF-Token": csrf_token}

    client.patch("/api/v1/settings", json={"language": "en", "region": "GB"}, headers=headers)
    rejected = client.post(
        "/api/v1/test/reset",
        json={"confirmation": "delete"},
        headers=headers,
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "confirmation_mismatch"

    reset = client.post(
        "/api/v1/test/reset",
        json={"confirmation": "DELETE ALL TEST DATA"},
        headers=headers,
    )
    assert reset.status_code == 200
    assert reset.json()["environment"] == "test"
    assert reset.json()["reset_generation"] == 1

    current = client.get("/api/v1/auth/session")
    assert current.json()["settings"]["language"] == "sv"
    assert current.json()["settings"]["region"] == "SE"
