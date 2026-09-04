from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "safety-owner",
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


def test_reconciliation_creates_explicit_non_consumption_adjustment_and_audit(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "account_type": "current",
            "opening_balance": "1000",
            "opening_balance_date": "2026-01-01",
            "currency": "SEK",
        },
    ).json()
    expense = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["account_id"],
            "transaction_kind": "expense",
            "transaction_date": "2026-01-10",
            "posting_date": "2026-01-10",
            "description": "Mat",
            "original_amount": "100",
            "original_currency": "SEK",
        },
    )
    assert expense.status_code == 201, expense.text
    snapshot = client.post(
        f"/api/v1/accounts/{account['account_id']}/snapshots",
        headers=headers,
        json={"valuation_date": "2026-01-31", "reported_balance": "950"},
    ).json()
    assert snapshot["calculated_balance"] == "900.0000"
    assert snapshot["difference"] == "50.0000"

    rejected = client.post(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}/adjustment",
        headers=headers,
        json={"confirmation": "yes"},
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "confirmation_mismatch"

    created = client.post(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}/adjustment",
        headers=headers,
        json={"confirmation": "CREATE BALANCE ADJUSTMENT"},
    )
    assert created.status_code == 201, created.text
    adjustment = created.json()
    assert adjustment["transaction_kind"] == "adjustment"
    assert adjustment["adjustment_direction"] == "increase"
    assert adjustment["original_amount"] == "50.0000"
    assert adjustment["source_type"] == "system"

    reconciled = client.get(
        f"/api/v1/accounts/{account['account_id']}/snapshots"
    ).json()[0]
    assert reconciled["calculated_balance"] == "950.0000"
    assert reconciled["difference"] == "0.0000"

    summary = client.get(
        "/api/v1/transactions/summary?date_from=2026-01-01&date_to=2026-01-31"
    ).json()
    assert summary["expenses"] == "100.0000"
    assert summary["income"] == "0.0000"
    assert summary["transaction_count"] == 1
    analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-01-01&date_to=2026-01-31"
    )
    assert analysis.status_code == 200, analysis.text

    duplicate = client.post(
        f"/api/v1/account-snapshots/{snapshot['account_snapshot_id']}/adjustment",
        headers=headers,
        json={"confirmation": "CREATE BALANCE ADJUSTMENT"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "snapshot_already_adjusted"

    audit = client.get(
        f"/api/v1/audit-events?entity_type=account_snapshot&entity_id={snapshot['account_snapshot_id']}"
    )
    assert audit.status_code == 200
    assert audit.json()["items"][0]["action"] == "balance_adjusted"
    assert audit.json()["items"][0]["changes"]["transaction_id"] == adjustment[
        "transaction_id"
    ]


def test_archived_items_are_visible_in_recycle_bin_and_restorable(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Tillfälligt konto",
            "account_type": "current",
            "opening_balance": "0",
            "opening_balance_date": "2026-01-01",
            "currency": "SEK",
        },
    ).json()
    archived = client.post(
        f"/api/v1/accounts/{account['account_id']}/archive", headers=headers
    )
    assert archived.status_code == 200

    recycle_bin = client.get("/api/v1/recycle-bin")
    assert recycle_bin.status_code == 200
    assert recycle_bin.json() == [
        {
            "entity_type": "account",
            "entity_id": account["account_id"],
            "label": "Tillfälligt konto",
            "archived_at": archived.json()["archived_at"],
            "restore_path": f"/accounts/{account['account_id']}/restore",
        }
    ]

    restored = client.post(
        f"/api/v1/accounts/{account['account_id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert client.get("/api/v1/recycle-bin").json() == []

    audit = client.get(
        f"/api/v1/audit-events?entity_type=account&entity_id={account['account_id']}"
    ).json()["items"]
    assert [item["action"] for item in audit] == ["restored", "archived", "created"]
