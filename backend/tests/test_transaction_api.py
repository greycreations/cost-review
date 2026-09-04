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
        "perspective": "total",
    }

    analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert analysis.status_code == 200
    assert analysis.json() == {
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "base_currency": "SEK",
        "daily": [
            {
                "date": "2026-08-20",
                "income": "30000.0000",
                "expenses": "425.3500",
                "net_cash_flow": "29574.6500",
            }
        ],
        "expense_categories": [
            {
                "category_id": data["expense"]["category_id"],
                "category_name": "Mat",
                "amount": "425.3500",
                "transaction_count": 1,
            }
        ],
        "comparison": None,
        "perspective": "total",
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

    unresolved_analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert unresolved_analysis.status_code == 200
    assert unresolved_analysis.json()["daily"] == []
    assert unresolved_analysis.json()["expense_categories"] == []

    resolved = client.patch(
        f"/api/v1/transactions/{missing.json()['transaction_id']}",
        headers=headers,
        json={"fx_rate": "1.52"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["converted_amount"] == "190.7600"
    assert resolved.json()["fx_rate"] == "1.5200000000"
    assert resolved.json()["fx_rate_status"] == "manual"

    resolved_analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert resolved_analysis.status_code == 200
    assert resolved_analysis.json()["expense_categories"][0]["amount"] == "190.7600"

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


def test_sharing_allocations_drive_total_and_my_share_analysis(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    me = client.post(
        "/api/v1/sharing-parties",
        headers=headers,
        json={"name": "Jag", "is_self": True},
    ).json()
    partner = client.post(
        "/api/v1/sharing-parties",
        headers=headers,
        json={"name": "Partner", "is_self": False},
    ).json()
    allocations = [
        {"sharing_party_id": me["sharing_party_id"], "percentage": "40"},
        {"sharing_party_id": partner["sharing_party_id"], "percentage": "60"},
    ]

    created = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            original_amount="100",
            sharing_allocations=allocations,
        ),
    )
    assert created.status_code == 201, created.text
    assert created.json()["sharing_allocations"] == [
        {
            "sharing_party_id": me["sharing_party_id"],
            "percentage": "40.0000",
            "is_self": True,
        },
        {
            "sharing_party_id": partner["sharing_party_id"],
            "percentage": "60.0000",
            "is_self": False,
        },
    ]

    total = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
        "&perspective=total"
    ).json()
    mine = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
        "&perspective=my_share"
    ).json()
    assert total["expenses"] == "100.0000"
    assert total["perspective"] == "total"
    assert mine["expenses"] == "40.0000"
    assert mine["perspective"] == "my_share"

    invalid = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            sharing_allocations=[
                {"sharing_party_id": me["sharing_party_id"], "percentage": "90"}
            ],
        ),
    )
    assert invalid.status_code == 422

    updated = client.patch(
        f"/api/v1/transactions/{created.json()['transaction_id']}",
        headers=headers,
        json={
            "sharing_allocations": [
                {"sharing_party_id": me["sharing_party_id"], "percentage": "25"},
                {
                    "sharing_party_id": partner["sharing_party_id"],
                    "percentage": "75",
                },
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    mine_after_update = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-01&date_to=2026-08-31"
        "&perspective=my_share"
    ).json()
    assert mine_after_update["perspective"] == "my_share"
    assert mine_after_update["expense_categories"][0]["amount"] == "25.0000"

    refund = client.post(
        f"/api/v1/transactions/{created.json()['transaction_id']}/refunds",
        headers=headers,
        json={
            "account_id": data["account"]["account_id"],
            "transaction_date": "2026-08-22",
            "posting_date": "2026-08-22",
            "description": "Delvis återbetalning",
            "original_amount": "20",
            "original_currency": "SEK",
        },
    )
    assert refund.status_code == 201, refund.text
    mine_after_refund = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-01&date_to=2026-08-31"
        "&perspective=my_share"
    ).json()
    assert mine_after_refund["expenses"] == "20.0000"

    budget = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "Delad matbudget",
            "amount": "100",
            "currency": "SEK",
            "period_type": "calendar_month",
            "rollover_mode": "reset",
            "starts_on": "2026-08-01",
        },
    )
    assert budget.status_code == 201, budget.text
    budget_id = budget.json()["budget_id"]
    total_budget = client.get(
        f"/api/v1/budgets/{budget_id}/outcome"
        "?date_from=2026-08-01&date_to=2026-08-31&perspective=total"
    ).json()
    my_budget = client.get(
        f"/api/v1/budgets/{budget_id}/outcome"
        "?date_from=2026-08-01&date_to=2026-08-31&perspective=my_share"
    ).json()
    assert total_budget["actual_amount"] == "80.0000"
    assert total_budget["perspective"] == "total"
    assert my_budget["actual_amount"] == "20.0000"
    assert my_budget["perspective"] == "my_share"
    my_budget_rows = client.get(
        f"/api/v1/budgets/{budget_id}/transactions"
        "?date_from=2026-08-01&date_to=2026-08-31&perspective=my_share"
    ).json()
    assert [row["matched_amount"] for row in my_budget_rows] == ["-5.0000", "25.0000"]

    split_id = created.json()["splits"][0]["transaction_split_id"]
    with pytest.raises(IntegrityError), client.app.state.database.engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM transaction_split_shares "
                "WHERE transaction_split_id = :split_id"
            ),
            {"split_id": split_id},
        )
        connection.execute(
            text(
                "INSERT INTO transaction_split_shares "
                "(transaction_split_id, sharing_party_id, percentage) "
                "VALUES (:split_id, :party_id, 90)"
            ),
            {"split_id": split_id, "party_id": me["sharing_party_id"]},
        )


def test_split_transactions_comparison_and_category_filter_share_one_semantics(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    travel = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Resor", "category_kind": "expense"},
    ).json()

    previous = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            transaction_date="2026-08-01",
            posting_date="2026-08-01",
            description="Tidigare mat",
            original_amount="300",
            category_id=data["expense"]["category_id"],
            tag_ids=[],
            is_base_cost=False,
        ),
    )
    assert previous.status_code == 201

    split_response = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            transaction_date="2026-08-20",
            description="Delat kvitto",
            original_amount="1000",
            category_id=None,
            tag_ids=[],
            is_base_cost=False,
            splits=[
                {
                    "original_amount": "600",
                    "category_id": data["expense"]["category_id"],
                    "tag_ids": [data["tag"]["tag_id"]],
                    "is_base_cost": True,
                    "memo": "Mat",
                },
                {
                    "original_amount": "400",
                    "category_id": travel["category_id"],
                    "tag_ids": [],
                    "is_base_cost": False,
                    "memo": "Tågbiljett",
                },
            ],
        ),
    )
    assert split_response.status_code == 201, split_response.text
    split_transaction = split_response.json()
    assert split_transaction["is_split"] is True
    assert [item["original_amount"] for item in split_transaction["splits"]] == [
        "600.0000",
        "400.0000",
    ]
    assert [item["converted_amount"] for item in split_transaction["splits"]] == [
        "600.0000",
        "400.0000",
    ]

    rejected_legacy_update = client.patch(
        f"/api/v1/transactions/{split_transaction['transaction_id']}",
        headers=headers,
        json={"category_id": travel["category_id"]},
    )
    assert rejected_legacy_update.status_code == 422
    assert rejected_legacy_update.json()["error"]["code"] == "split_update_required"

    updated_split = client.patch(
        f"/api/v1/transactions/{split_transaction['transaction_id']}",
        headers=headers,
        json={
            "description": "Delat kvitto, granskat",
            "splits": [
                {
                    "original_amount": "600",
                    "category_id": data["expense"]["category_id"],
                    "tag_ids": [data["tag"]["tag_id"]],
                    "is_base_cost": True,
                    "memo": "Mat",
                },
                {
                    "original_amount": "400",
                    "category_id": travel["category_id"],
                    "tag_ids": [],
                    "is_base_cost": False,
                    "memo": "Tågbiljett",
                },
            ],
        },
    )
    assert updated_split.status_code == 200, updated_split.text
    assert updated_split.json()["description"] == "Delat kvitto, granskat"

    refund = client.post(
        f"/api/v1/transactions/{split_transaction['transaction_id']}/refunds",
        headers=headers,
        json={
            "account_id": data["account"]["account_id"],
            "transaction_date": "2026-08-21",
            "posting_date": "2026-08-21",
            "description": "Delåterbetalning",
            "original_amount": "100",
            "original_currency": "SEK",
        },
    )
    assert refund.status_code == 201, refund.text

    analysis = client.get(
        "/api/v1/transactions/analysis?date_from=2026-08-10&date_to=2026-08-31"
        "&comparison=previous_period"
    )
    assert analysis.status_code == 200, analysis.text
    result = analysis.json()
    assert result["expense_categories"] == [
        {
            "category_id": data["expense"]["category_id"],
            "category_name": "Mat",
            "amount": "540.0000",
            "transaction_count": 2,
        },
        {
            "category_id": travel["category_id"],
            "category_name": "Resor",
            "amount": "360.0000",
            "transaction_count": 2,
        },
    ]
    assert result["comparison"]["date_from"] == "2026-07-19"
    assert result["comparison"]["date_to"] == "2026-08-09"
    assert result["comparison"]["expenses"] == "300.0000"

    filtered_summary = client.get(
        "/api/v1/transactions/summary?date_from=2026-08-10&date_to=2026-08-31"
        f"&category_id={data['expense']['category_id']}"
    )
    assert filtered_summary.status_code == 200
    assert filtered_summary.json()["expenses"] == "540.0000"
    filtered_list = client.get(
        f"/api/v1/transactions?category_id={data['expense']['category_id']}"
    ).json()
    assert {item["transaction_kind"] for item in filtered_list["items"]} == {
        "expense",
        "refund",
    }
    impossible_cross_split_match = client.get(
        "/api/v1/transactions"
        f"?category_id={travel['category_id']}&tag_id={data['tag']['tag_id']}"
    ).json()
    assert impossible_cross_split_match["total"] == 0


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
