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
    assert status.json()["registration_allowed"] is True
    assert status.json()["data_plane_id"] == health.json()["data_plane_id"]


def test_setup_locks_and_creates_environment_scoped_session(
    client: TestClient, settings: Settings
) -> None:
    response = client.post("/api/v1/setup", json=SETUP_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["username"] == "platform-owner"
    assert response.json()["is_admin"] is True
    assert response.json()["environment"] == "test"
    assert client.cookies.get(settings.session_cookie_name)
    assert client.cookies.get(settings.csrf_cookie_name)

    locked = client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert locked.status_code == 409
    assert locked.json()["error"]["code"] == "setup_locked"

    current = client.get("/api/v1/auth/session")
    assert current.status_code == 200
    assert current.json()["settings"]["timezone"] == "Europe/Stockholm"


def test_self_registration_creates_a_non_admin_account(
    client: TestClient, settings: Settings
) -> None:
    client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    owner_id = client.get("/api/v1/users").json()[0]["user_id"]
    client.cookies.clear()

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "username": "household-member",
            "password": "a long member password",
            "settings": {"language": "en"},
        },
    )
    assert registered.status_code == 201
    assert registered.json()["username"] == "household-member"
    assert registered.json()["is_admin"] is False
    assert registered.json()["settings"]["language"] == "en"

    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    denied = client.get("/api/v1/users")
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "admin_required"

    denied_delete = client.request(
        "DELETE",
        f"/api/v1/users/{owner_id}",
        json={"confirmation": "DELETE platform-owner"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert denied_delete.status_code == 403
    assert denied_delete.json()["error"]["code"] == "admin_required"

    changed = client.patch(
        "/api/v1/auth/password",
        json={
            "current_password": "a long member password",
            "new_password": "a different long password",
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert changed.status_code == 204

    client.cookies.clear()
    old_login = client.post(
        "/api/v1/auth/login",
        json={"username": "household-member", "password": "a long member password"},
    )
    assert old_login.status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": "household-member", "password": "a different long password"},
    )
    assert new_login.status_code == 200


def test_admin_can_fully_manage_other_accounts(client: TestClient, settings: Settings) -> None:
    client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    headers = {"X-CSRF-Token": csrf_token}

    created = client.post(
        "/api/v1/users",
        json={
            "username": "managed-user",
            "password": "managed user password",
            "is_admin": False,
        },
        headers=headers,
    )
    assert created.status_code == 201
    user_id = created.json()["user_id"]

    listed = client.get("/api/v1/users")
    assert listed.status_code == 200
    assert [item["username"] for item in listed.json()] == ["managed-user", "platform-owner"]

    updated = client.patch(
        f"/api/v1/users/{user_id}",
        json={"username": "renamed-user", "is_admin": True},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["username"] == "renamed-user"
    assert updated.json()["is_admin"] is True

    reset = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        json={"new_password": "administrator reset password"},
        headers=headers,
    )
    assert reset.status_code == 204

    mismatch = client.request(
        "DELETE",
        f"/api/v1/users/{user_id}",
        json={"confirmation": "DELETE wrong-user"},
        headers=headers,
    )
    assert mismatch.status_code == 422
    deleted = client.request(
        "DELETE",
        f"/api/v1/users/{user_id}",
        json={"confirmation": "DELETE renamed-user"},
        headers=headers,
    )
    assert deleted.status_code == 204
    assert [item["username"] for item in client.get("/api/v1/users").json()] == [
        "platform-owner"
    ]


def test_admin_guards_own_account_and_the_final_admin(
    client: TestClient, settings: Settings
) -> None:
    setup = client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    csrf_token = client.cookies.get(settings.csrf_cookie_name)
    headers = {"X-CSRF-Token": csrf_token}
    owner = client.get("/api/v1/users").json()[0]

    demote = client.patch(
        f"/api/v1/users/{owner['user_id']}",
        json={"is_admin": False},
        headers=headers,
    )
    assert demote.status_code == 409
    assert demote.json()["error"]["code"] == "last_admin_required"

    delete_self = client.request(
        "DELETE",
        f"/api/v1/users/{owner['user_id']}",
        json={"confirmation": "DELETE platform-owner"},
        headers=headers,
    )
    assert delete_self.status_code == 422
    assert delete_self.json()["error"]["code"] == "cannot_delete_self"
    assert setup.json()["is_admin"] is True


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
