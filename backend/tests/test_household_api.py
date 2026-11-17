"""Household access model: one shared ledger, role-based access, personal My Share."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from tests.test_transaction_api import (
    authenticate,
    seed_master_data,
    transaction_payload,
)

MEMBER_PASSWORD = "household member password"
VIEWER_PASSWORD = "household viewer password"
SUMMARY = "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"


def create_member(
    client: TestClient, headers: dict[str, str], username: str, role: str, password: str
) -> int:
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={"username": username, "password": password, "role": role},
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == role
    return response.json()["user_id"]


def sign_in(
    client: TestClient, settings: Settings, username: str, password: str
) -> dict[str, str]:
    client.cookies.clear()
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"X-CSRF-Token": client.cookies.get(settings.csrf_cookie_name)}


def test_roles_separate_reading_writing_and_household_administration(
    client: TestClient, settings: Settings
) -> None:
    owner_headers = authenticate(client, settings)
    data = seed_master_data(client, owner_headers)
    create_member(client, owner_headers, "partner", "member", MEMBER_PASSWORD)
    create_member(client, owner_headers, "accountant", "viewer", VIEWER_PASSWORD)

    viewer_headers = sign_in(client, settings, "accountant", VIEWER_PASSWORD)
    assert client.get("/api/v1/accounts").status_code == 200
    members = client.get("/api/v1/household/members").json()
    assert {(item["username"], item["role"]) for item in members} == {
        ("transaction-owner", "owner"),
        ("partner", "member"),
        ("accountant", "viewer"),
    }
    assert all(set(item) == {"user_id", "username", "role"} for item in members)
    assert client.get(SUMMARY).status_code == 200
    denied_write = client.post(
        "/api/v1/transactions", headers=viewer_headers, json=transaction_payload(data)
    )
    assert denied_write.status_code == 403
    assert denied_write.json()["error"]["code"] == "read_only_member"
    # A viewer still manages their own session and preferences.
    assert (
        client.patch(
            "/api/v1/settings", headers=viewer_headers, json={"language": "en"}
        ).status_code
        == 200
    )

    member_headers = sign_in(client, settings, "partner", MEMBER_PASSWORD)
    created = client.post(
        "/api/v1/transactions", headers=member_headers, json=transaction_payload(data)
    )
    assert created.status_code == 201
    for method, path in (
        ("GET", "/api/v1/users"),
        ("GET", "/api/v1/backups"),
        ("POST", "/api/v1/backups"),
        ("POST", "/api/v1/test/reset"),
    ):
        response = client.request(
            method,
            path,
            headers=member_headers,
            json={"confirmation": "DELETE ALL TEST DATA"} if path.endswith("reset") else None,
        )
        assert response.status_code == 403, (method, path, response.text)
        assert response.json()["error"]["code"] == "owner_required"


def test_my_share_is_personal_to_each_household_member(
    client: TestClient, settings: Settings
) -> None:
    owner_headers = authenticate(client, settings)
    owner_id = client.get("/api/v1/auth/session").json()["user_id"]
    data = seed_master_data(client, owner_headers)
    partner_id = create_member(client, owner_headers, "partner", "member", MEMBER_PASSWORD)
    create_member(client, owner_headers, "lodger", "member", "lodger member password")

    owner_party = client.post(
        "/api/v1/sharing-parties",
        headers=owner_headers,
        json={"name": "Anders", "user_id": owner_id},
    ).json()
    partner_party = client.post(
        "/api/v1/sharing-parties",
        headers=owner_headers,
        json={"name": "Partner", "user_id": partner_id},
    ).json()
    created = client.post(
        "/api/v1/transactions",
        headers=owner_headers,
        json=transaction_payload(
            data,
            original_amount="1000",
            sharing_allocations=[
                {"sharing_party_id": owner_party["sharing_party_id"], "percentage": "30"},
                {"sharing_party_id": partner_party["sharing_party_id"], "percentage": "70"},
            ],
        ),
    )
    assert created.status_code == 201, created.text

    assert client.get(f"{SUMMARY}&perspective=my_share").json()["expenses"] == "300.0000"
    assert client.get(f"{SUMMARY}&perspective=total").json()["expenses"] == "1000.0000"

    sign_in(client, settings, "partner", MEMBER_PASSWORD)
    assert client.get(f"{SUMMARY}&perspective=my_share").json()["expenses"] == "700.0000"

    # A member without a linked sharing party owns none of an allocated expense.
    sign_in(client, settings, "lodger", "lodger member password")
    assert client.get(f"{SUMMARY}&perspective=my_share").json()["expenses"] == "0.0000"


def test_audit_events_name_the_household_member_who_changed_the_ledger(
    client: TestClient, settings: Settings
) -> None:
    owner_headers = authenticate(client, settings)
    data = seed_master_data(client, owner_headers)
    partner_id = create_member(client, owner_headers, "partner", "member", MEMBER_PASSWORD)

    member_headers = sign_in(client, settings, "partner", MEMBER_PASSWORD)
    created = client.post(
        "/api/v1/transactions", headers=member_headers, json=transaction_payload(data)
    ).json()

    events = client.get(
        "/api/v1/audit-events",
        params={"entity_type": "transaction", "entity_id": created["transaction_id"]},
    ).json()["items"]
    assert events
    assert {event["actor_user_id"] for event in events} == {partner_id}


def test_repeated_failed_sign_ins_lock_the_account_temporarily(
    client: TestClient, settings: Settings
) -> None:
    authenticate(client, settings)
    client.cookies.clear()

    for _ in range(4):
        failed = client.post(
            "/api/v1/auth/login",
            json={"username": "transaction-owner", "password": "wrong password"},
        )
        assert failed.status_code == 401
    locking = client.post(
        "/api/v1/auth/login",
        json={"username": "transaction-owner", "password": "wrong password"},
    )
    assert locking.status_code == 401

    locked = client.post(
        "/api/v1/auth/login",
        json={"username": "transaction-owner", "password": "correct horse battery staple"},
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "account_temporarily_locked"
    assert locked.json()["error"]["details"][0]["retry_after_seconds"] > 0

    unknown = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody-here", "password": "wrong password"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["error"]["code"] == "invalid_credentials"


def test_successful_sign_in_clears_earlier_failures(
    client: TestClient, settings: Settings
) -> None:
    authenticate(client, settings)
    client.cookies.clear()
    for _ in range(4):
        client.post(
            "/api/v1/auth/login",
            json={"username": "transaction-owner", "password": "wrong password"},
        )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "transaction-owner", "password": "correct horse battery staple"},
        ).status_code
        == 200
    )
    for _ in range(4):
        assert (
            client.post(
                "/api/v1/auth/login",
                json={"username": "transaction-owner", "password": "wrong password"},
            ).status_code
            == 401
        )
