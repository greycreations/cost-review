from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "transfer-owner",
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


def create_account(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str,
    account_type: str,
    currency: str,
) -> dict:
    response = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": name,
            "account_type": account_type,
            "opening_balance": "1000",
            "opening_balance_date": "2026-08-01",
            "currency": currency,
        },
    )
    assert response.status_code == 201
    return response.json()


def transfer_payload(source_id: int, destination_id: int, **overrides) -> dict:
    payload = {
        "source_account_id": source_id,
        "destination_account_id": destination_id,
        "purpose": "internal",
        "transaction_date": "2026-08-22",
        "source_posting_date": "2026-08-22",
        "destination_posting_date": "2026-08-23",
        "description": "Mellan egna konton",
        "source_amount": "250.00",
        "destination_amount": "250.00",
    }
    payload.update(overrides)
    return payload


def test_credit_card_payment_is_atomic_and_excluded_from_income_expense(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    current = create_account(
        client, headers, name="Vardagskonto", account_type="current", currency="SEK"
    )
    card = create_account(
        client, headers, name="Kreditkort", account_type="credit_card", currency="SEK"
    )

    created_response = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(
            current["account_id"],
            card["account_id"],
            purpose="credit_card_payment",
            description="Betalning av kortfaktura",
        ),
    )
    assert created_response.status_code == 201
    created = created_response.json()
    assert created["purpose"] == "credit_card_payment"
    assert created["source_amount"] == "250.0000"
    assert created["destination_amount"] == "250.0000"
    assert created["source_currency"] == "SEK"
    assert created["destination_currency"] == "SEK"
    assert created["source_fx_rate_status"] == "not_required"
    assert created["status"] == "active"

    assert client.get("/api/v1/transactions").json()["total"] == 0
    summary = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert summary["income"] == "0.0000"
    assert summary["expenses"] == "0.0000"
    assert summary["net_cash_flow"] == "0.0000"
    assert summary["transaction_count"] == 0
    analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert analysis["daily"] == []
    assert analysis["expense_categories"] == []

    by_source = client.get(f"/api/v1/transfers?account_id={current['account_id']}")
    by_destination = client.get(f"/api/v1/transfers?account_id={card['account_id']}")
    assert by_source.json()["total"] == 1
    assert by_destination.json()["total"] == 1

    with client.app.state.database.engine.connect() as connection:
        outgoing_id = connection.scalar(
            text(
                "SELECT outgoing_transaction_id FROM transfer_links "
                "WHERE transfer_link_id = :transfer_id"
            ),
            {"transfer_id": created["transfer_link_id"]},
        )
        assert connection.scalar(
            text("SELECT count(*) FROM transactions WHERE transaction_kind = 'transfer'")
        ) == 2
    hidden_leg = client.get(f"/api/v1/transactions/{outgoing_id}")
    assert hidden_leg.status_code == 404

    updated = client.patch(
        f"/api/v1/transfers/{created['transfer_link_id']}",
        headers=headers,
        json={
            "description": "Kortfaktura augusti",
            "source_amount": "300",
            "destination_amount": "300",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["description"] == "Kortfaktura augusti"
    assert updated.json()["source_amount"] == "300.0000"

    archived = client.post(
        f"/api/v1/transfers/{created['transfer_link_id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/transfers").json()["total"] == 0
    assert client.get("/api/v1/transfers?include_archived=true").json()["total"] == 1
    with client.app.state.database.engine.connect() as connection:
        statuses = connection.execute(
            text(
                "SELECT status FROM transactions WHERE transaction_kind = 'transfer' "
                "ORDER BY transaction_id"
            )
        ).scalars()
        assert list(statuses) == ["archived", "archived"]

    restored = client.post(
        f"/api/v1/transfers/{created['transfer_link_id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_cross_currency_transfer_preserves_both_amounts_and_effective_fx(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    sek = create_account(
        client, headers, name="SEK-konto", account_type="current", currency="SEK"
    )
    eur = create_account(
        client, headers, name="EUR-konto", account_type="savings", currency="EUR"
    )

    created = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(
            sek["account_id"],
            eur["account_id"],
            source_amount="100",
            destination_amount="8.75",
            purpose="savings",
        ),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["source_amount"] == "100.0000"
    assert body["destination_amount"] == "8.7500"
    assert body["source_converted_amount"] == "100.0000"
    assert body["destination_converted_amount"] == "100.0000"
    assert body["destination_fx_rate"] == "11.4285714286"
    assert body["destination_fx_rate_status"] == "manual"

    mismatched_value = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(
            sek["account_id"],
            eur["account_id"],
            source_amount="100",
            destination_amount="8.75",
            destination_converted_amount="99",
        ),
    )
    assert mismatched_value.status_code == 422
    assert mismatched_value.json()["error"]["code"] == "transfer_value_mismatch"


def test_transfer_invariants_and_demo_reset_are_database_enforced(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    source = create_account(
        client, headers, name="Från", account_type="current", currency="SEK"
    )
    destination = create_account(
        client, headers, name="Till", account_type="savings", currency="SEK"
    )

    same_account = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(source["account_id"], source["account_id"]),
    )
    assert same_account.status_code == 422

    amount_mismatch = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(
            source["account_id"],
            destination["account_id"],
            destination_amount="249",
        ),
    )
    assert amount_mismatch.status_code == 422
    assert amount_mismatch.json()["error"]["code"] == (
        "same_currency_transfer_amount_mismatch"
    )

    purpose_mismatch = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(
            source["account_id"],
            destination["account_id"],
            purpose="credit_card_payment",
        ),
    )
    assert purpose_mismatch.status_code == 422
    assert purpose_mismatch.json()["error"]["code"] == (
        "transfer_destination_type_mismatch"
    )

    created = client.post(
        "/api/v1/transfers",
        headers=headers,
        json=transfer_payload(source["account_id"], destination["account_id"]),
    )
    assert created.status_code == 201

    with (
        pytest.raises(IntegrityError),
        client.app.state.database.engine.begin() as connection,
    ):
        connection.execute(
            text(
                "UPDATE transfer_links SET purpose = 'credit_card_payment' "
                "WHERE transfer_link_id = :transfer_id"
            ),
            {"transfer_id": created.json()["transfer_link_id"]},
        )

    with (
        pytest.raises(IntegrityError),
        client.app.state.database.engine.begin() as connection,
    ):
        connection.execute(
            text(
                "UPDATE transactions SET original_amount = 249, converted_amount = 249 "
                "WHERE transaction_id = (SELECT incoming_transaction_id FROM transfer_links "
                "WHERE transfer_link_id = :transfer_id)"
            ),
            {"transfer_id": created.json()["transfer_link_id"]},
        )
        connection.execute(
            text(
                "UPDATE transaction_splits SET original_amount = 249, converted_amount = 249 "
                "WHERE transaction_id = (SELECT incoming_transaction_id FROM transfer_links "
                "WHERE transfer_link_id = :transfer_id)"
            ),
            {"transfer_id": created.json()["transfer_link_id"]},
        )

    reset = client.post(
        "/api/v1/test/reset",
        headers=headers,
        json={"confirmation": "DELETE ALL TEST DATA"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/transfers").json()["total"] == 0
    with client.app.state.database.engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM transfer_links")) == 0
        assert connection.scalar(text("SELECT count(*) FROM transactions")) == 0
