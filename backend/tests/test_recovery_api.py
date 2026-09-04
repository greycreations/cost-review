from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import Settings

SETUP = {
    "username": "recovery-owner",
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


def test_refunds_and_reimbursements_preserve_gross_cost_and_reduce_analysis(
    client: TestClient, settings: Settings
) -> None:
    headers, account_id, category_id, expense = _seed(client, settings)

    refund = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/refunds",
        headers=headers,
        json=_recovery_payload(account_id, "Butiksretur", "250"),
    )
    assert refund.status_code == 201, refund.text
    assert refund.json()["transaction_kind"] == "refund"
    assert refund.json()["linked_expense_id"] == expense["transaction_id"]
    assert refund.json()["category_id"] is None

    reimbursement = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/reimbursements",
        headers=headers,
        json=_recovery_payload(account_id, "Swish från hushållet", "300"),
    )
    assert reimbursement.status_code == 201, reimbursement.text
    assert reimbursement.json()["transaction_kind"] == "reimbursement"

    original = client.get(f"/api/v1/transactions/{expense['transaction_id']}").json()
    assert original["original_amount"] == "1000.0000"

    listed = client.get("/api/v1/transactions").json()
    assert listed["total"] == 3
    assert {item["transaction_kind"] for item in listed["items"]} == {
        "expense",
        "refund",
        "reimbursement",
    }
    category_filtered = client.get(f"/api/v1/transactions?category_id={category_id}").json()
    assert category_filtered["total"] == 3

    summary = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert summary["income"] == "0.0000"
    assert summary["expenses"] == "450.0000"
    assert summary["net_cash_flow"] == "-450.0000"
    assert summary["transaction_count"] == 3

    analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert analysis["expense_categories"] == [
        {
            "category_id": category_id,
            "category_name": "Resor",
            "amount": "450.0000",
            "transaction_count": 3,
        }
    ]

    archived = client.post(
        f"/api/v1/recoveries/{refund.json()['transaction_id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    after_archive = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert after_archive["expenses"] == "700.0000"

    restored = client.post(
        f"/api/v1/recoveries/{refund.json()['transaction_id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    blocked_archive = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/archive", headers=headers
    )
    assert blocked_archive.status_code == 409


def test_recovery_invariants_reject_invalid_dates_and_excess_amounts(
    client: TestClient, settings: Settings
) -> None:
    headers, account_id, _, expense = _seed(client, settings)
    before = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/refunds",
        headers=headers,
        json=_recovery_payload(
            account_id, "För tidig återbetalning", "10", transaction_date="2026-08-09"
        ),
    )
    assert before.status_code == 422
    assert before.json()["error"]["code"] == "recovery_before_expense"

    excessive = client.post(
        f"/api/v1/transactions/{expense['transaction_id']}/reimbursements",
        headers=headers,
        json=_recovery_payload(account_id, "För stor ersättning", "1000.01"),
    )
    assert excessive.status_code == 409
    assert excessive.json()["error"]["code"] == "recovery_integrity_conflict"

    with pytest.raises(IntegrityError), client.app.state.database.engine.begin() as connection:
        transaction_id = connection.scalar(
            text(
                "INSERT INTO transactions (account_id, transaction_kind, transaction_date, "
                "posting_date, description, normalized_description, original_amount, "
                "original_currency, converted_amount, base_currency, fx_rate, fx_rate_status, "
                "source_type, status) VALUES (:account_id, 'refund', '2026-08-20', "
                "'2026-08-20', 'Unlinked refund', 'unlinked refund', 10, 'SEK', 10, 'SEK', "
                "1, 'not_required', 'manual', 'active') RETURNING transaction_id"
            ),
            {"account_id": account_id},
        )
        connection.execute(
            text(
                "INSERT INTO transaction_splits (transaction_id, original_amount, "
                "converted_amount, is_base_cost) VALUES (:transaction_id, 10, 10, false)"
            ),
            {"transaction_id": transaction_id},
        )


def _seed(client: TestClient, settings: Settings):
    setup = client.post("/api/v1/setup", json=SETUP)
    assert setup.status_code == 201
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf
    headers = {"X-CSRF-Token": csrf}
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "account_type": "current",
            "opening_balance": "0",
            "opening_balance_date": "2026-08-01",
            "currency": "SEK",
        },
    ).json()
    category = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Resor", "category_kind": "expense"},
    ).json()
    expense_response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["account_id"],
            "transaction_kind": "expense",
            "transaction_date": "2026-08-10",
            "posting_date": "2026-08-10",
            "description": "Tågbiljetter",
            "original_amount": "1000",
            "original_currency": "SEK",
            "category_id": category["category_id"],
        },
    )
    assert expense_response.status_code == 201
    return headers, account["account_id"], category["category_id"], expense_response.json()


def _recovery_payload(
    account_id: int,
    description: str,
    amount: str,
    *,
    transaction_date: str = "2026-08-20",
) -> dict[str, object]:
    return {
        "account_id": account_id,
        "transaction_date": transaction_date,
        "posting_date": transaction_date,
        "description": description,
        "original_amount": amount,
        "original_currency": "SEK",
    }
