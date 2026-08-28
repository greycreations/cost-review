from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "snapshot-owner",
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


def authenticate(client: TestClient, settings: Settings) -> dict[str, str]:
    assert client.post("/api/v1/setup", json=SETUP_PAYLOAD).status_code == 201
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf
    return {"X-CSRF-Token": csrf}


def create_account(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Investeringskonto",
    account_type: str = "investment",
    currency: str = "SEK",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": name,
            "account_type": account_type,
            "opening_balance": "10000.00",
            "opening_balance_date": "2026-01-01",
            "currency": currency,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_snapshot_history_preserves_values_and_calculates_account_difference(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    account = create_account(client, headers)
    account_id = account["account_id"]

    created = client.post(
        f"/api/v1/accounts/{account_id}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-01-31", "reported_balance": "10750.25"},
    )
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["reported_balance"] == "10750.2500"
    assert snapshot["converted_balance"] == "10750.2500"
    assert snapshot["fx_rate"] == "1.0000000000"
    assert snapshot["fx_rate_status"] == "not_required"
    assert snapshot["calculated_balance"] == "10000.0000"
    assert snapshot["difference"] == "750.2500"

    duplicate = client.post(
        f"/api/v1/accounts/{account_id}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-01-31", "reported_balance": "11000"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "account_snapshot_date_exists"

    before_opening = client.post(
        f"/api/v1/accounts/{account_id}/snapshots",
        headers=headers,
        json={"valuation_date": "2025-12-31", "reported_balance": "9999"},
    )
    assert before_opening.status_code == 422
    assert before_opening.json()["error"]["code"] == "snapshot_before_account_opening"

    corrected = client.patch(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}",
        headers=headers,
        json={"reported_balance": "10800.50", "notes": "Månadsskifte"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["reported_balance"] == "10800.5000"

    history = client.get(f"/api/v1/accounts/{account_id}/snapshots")
    assert history.status_code == 200
    assert [item["valuation_date"] for item in history.json()] == ["2026-01-31"]


def test_snapshot_balance_uses_posting_date_and_transfer_direction(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    source = create_account(client, headers, name="Vardagskonto", account_type="current")
    destination = create_account(client, headers, name="Sparande", account_type="savings")
    transfer = client.post(
        "/api/v1/transfers",
        headers=headers,
        json={
            "source_account_id": source["account_id"],
            "destination_account_id": destination["account_id"],
            "purpose": "savings",
            "transaction_date": "2026-02-01",
            "source_posting_date": "2026-02-02",
            "destination_posting_date": "2026-02-03",
            "description": "Månadssparande",
            "source_amount": "1000",
            "destination_amount": "1000",
        },
    )
    assert transfer.status_code == 201

    source_snapshot = client.post(
        f"/api/v1/accounts/{source['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-02-02", "reported_balance": "9000"},
    )
    destination_before = client.post(
        f"/api/v1/accounts/{destination['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-02-02", "reported_balance": "10000"},
    )
    destination_after = client.post(
        f"/api/v1/accounts/{destination['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-02-03", "reported_balance": "11000"},
    )
    assert source_snapshot.json()["calculated_balance"] == "9000.0000"
    assert destination_before.json()["calculated_balance"] == "10000.0000"
    assert destination_after.json()["calculated_balance"] == "11000.0000"


def test_foreign_snapshot_can_remain_visible_with_missing_fx_and_archive_restore(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    account = create_account(client, headers, currency="EUR")
    created = client.post(
        f"/api/v1/accounts/{account['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-03-31", "reported_balance": "-125.50"},
    )
    assert created.status_code == 201
    snapshot = created.json()
    assert snapshot["currency"] == "EUR"
    assert snapshot["base_currency"] == "SEK"
    assert snapshot["converted_balance"] is None
    assert snapshot["fx_rate_status"] == "missing"

    archived = client.post(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}/archive",
        headers=headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get(f"/api/v1/accounts/{account['account_id']}/snapshots").json() == []

    restored = client.post(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}/restore",
        headers=headers,
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_calculated_balance_is_honestly_incomplete_without_account_currency_value(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    account = create_account(
        client, headers, name="SEK-konto", account_type="current", currency="SEK"
    )
    transaction = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["account_id"],
            "transaction_kind": "expense",
            "transaction_date": "2026-04-01",
            "posting_date": "2026-04-02",
            "description": "Köp utan historisk kurs",
            "original_amount": "25.00",
            "original_currency": "EUR",
        },
    )
    assert transaction.status_code == 201
    assert transaction.json()["fx_rate_status"] == "missing"

    snapshot = client.post(
        f"/api/v1/accounts/{account['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-04-30", "reported_balance": "9700"},
    )
    assert snapshot.status_code == 201
    assert snapshot.json()["calculation_status"] == "incomplete"
    assert snapshot.json()["calculated_balance"] is None
    assert snapshot.json()["difference"] is None
