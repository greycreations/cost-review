from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "transaction-owner",
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
    response = client.post("/api/v1/setup", json=SETUP_PAYLOAD)
    assert response.status_code == 201
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf
    return {"X-CSRF-Token": csrf}


def seed_master_data(client: TestClient, headers: dict[str, str]) -> dict[str, dict]:
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "account_type": "current",
            "opening_balance": "1000",
            "opening_balance_date": "2026-08-01",
            "currency": "SEK",
        },
    ).json()
    expense = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Mat", "category_kind": "expense"},
    ).json()
    income = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Lön", "category_kind": "income"},
    ).json()
    provider = client.post("/api/v1/providers", headers=headers, json={"name": "Matbutiken"}).json()
    tag = client.post("/api/v1/tags", headers=headers, json={"name": "Hushåll"}).json()
    return {
        "account": account,
        "expense": expense,
        "income": income,
        "provider": provider,
        "tag": tag,
    }


def transaction_payload(data: dict[str, dict], **overrides) -> dict:
    payload = {
        "account_id": data["account"]["account_id"],
        "provider_id": data["provider"]["provider_id"],
        "transaction_kind": "expense",
        "transaction_date": "2026-08-20",
        "posting_date": "2026-08-21",
        "description": "Veckohandling",
        "original_amount": "425.35",
        "original_currency": "SEK",
        "category_id": data["expense"]["category_id"],
        "tag_ids": [data["tag"]["tag_id"]],
        "is_base_cost": True,
    }
    payload.update(overrides)
    return payload


def test_manual_transaction_crud_filters_and_period_summary(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)

    expense_response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(data),
    )
    assert expense_response.status_code == 201
    expense = expense_response.json()
    assert expense["original_amount"] == "425.3500"
    assert expense["converted_amount"] == "425.3500"
    assert expense["fx_rate"] == "1.0000000000"
    assert expense["fx_rate_status"] == "not_required"
    assert expense["tag_ids"] == [data["tag"]["tag_id"]]

    income_response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            provider_id=None,
            transaction_kind="income",
            description="Lön augusti",
            original_amount="30000",
            category_id=data["income"]["category_id"],
            tag_ids=[],
            is_base_cost=False,
        ),
    )
    assert income_response.status_code == 201

    listed = client.get("/api/v1/transactions?search=veckohandling")
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["transaction_id"] == expense["transaction_id"]

    filtered = client.get(f"/api/v1/transactions?category_id={data['income']['category_id']}")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    summary = client.get("/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31")
    assert summary.status_code == 200
    assert summary.json() == {
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "base_currency": "SEK",
        "income": "30000.0000",
        "expenses": "425.3500",
        "net_cash_flow": "29574.6500",
        "transaction_count": 2,
        "missing_fx_count": 0,
    }

    updated = client.patch(
        f"/api/v1/transactions/{expense['transaction_id']}",
        headers=headers,
        json={"description": "Mat och hushåll", "original_amount": "500.10"},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Mat och hushåll"
    assert updated.json()["converted_amount"] == "500.1000"

    archived = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/transactions").json()["total"] == 1
    assert client.get("/api/v1/transactions?include_archived=true").json()["total"] == 2


def test_fx_gaps_are_preserved_and_excluded_from_canonical_totals(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)

    missing = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            description="Lunch i Danmark",
            original_amount="125.50",
            original_currency="DKK",
        ),
    )
    assert missing.status_code == 201
    assert missing.json()["converted_amount"] is None
    assert missing.json()["fx_rate"] is None
    assert missing.json()["fx_rate_status"] == "missing"

    resolved = client.patch(
        f"/api/v1/transactions/{missing.json()['transaction_id']}",
        headers=headers,
        json={"fx_rate": "1.52"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["converted_amount"] == "190.7600"
    assert resolved.json()["fx_rate"] == "1.5200000000"
    assert resolved.json()["fx_rate_status"] == "manual"

    invalid = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            original_currency="DKK",
            converted_amount="100",
            fx_rate="2",
        ),
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "fx_conversion_mismatch"


def test_category_semantics_database_balance_and_test_reset(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)

    wrong_category = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(data, category_id=data["income"]["category_id"]),
    )
    assert wrong_category.status_code == 422
    assert wrong_category.json()["error"]["code"] == "category_kind_mismatch"

    with (
        pytest.raises(IntegrityError),
        client.app.state.database.engine.begin() as connection,
    ):
        connection.execute(
            text(
                "INSERT INTO transactions (account_id, transaction_kind, transaction_date, "
                "posting_date, description, normalized_description, original_amount, "
                "original_currency, converted_amount, base_currency, fx_rate, "
                "fx_rate_status, source_type) VALUES (:account_id, 'expense', "
                "'2026-08-20', '2026-08-20', 'Invalid', 'invalid', 50, 'SEK', 50, "
                "'SEK', 1, 'not_required', 'manual')"
            ),
            {"account_id": data["account"]["account_id"]},
        )

    created = client.post("/api/v1/transactions", headers=headers, json=transaction_payload(data))
    assert created.status_code == 201
    reset = client.post(
        "/api/v1/test/reset",
        headers=headers,
        json={"confirmation": "DELETE ALL TEST DATA"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/transactions").json()["total"] == 0
