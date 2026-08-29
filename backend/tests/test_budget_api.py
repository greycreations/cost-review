from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "budget-owner",
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


def seed_budget_data(client: TestClient, headers: dict[str, str]) -> dict[str, dict]:
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "account_type": "current",
            "opening_balance": "0",
            "opening_balance_date": "2026-07-01",
            "currency": "SEK",
        },
    ).json()
    food = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Mat", "category_kind": "expense"},
    ).json()
    travel = client.post(
        "/api/v1/categories",
        headers=headers,
        json={"name": "Resor", "category_kind": "expense"},
    ).json()
    household = client.post("/api/v1/tags", headers=headers, json={"name": "Hushåll"}).json()
    return {"account": account, "food": food, "travel": travel, "tag": household}


def expense_payload(data: dict[str, dict], transaction_date: str, amount: str) -> dict:
    return {
        "account_id": data["account"]["account_id"],
        "provider_id": None,
        "transaction_kind": "expense",
        "transaction_date": transaction_date,
        "posting_date": transaction_date,
        "description": "Delat inköp",
        "original_amount": amount,
        "original_currency": "SEK",
        "category_id": data["food"]["category_id"],
        "tag_ids": [data["tag"]["tag_id"]],
        "is_base_cost": False,
    }


def budget_payload(data: dict[str, dict], **overrides) -> dict:
    payload = {
        "name": "Matbudget",
        "amount": "1000",
        "currency": "SEK",
        "period_type": "calendar_month",
        "rollover_mode": "reset",
        "starts_on": "2026-07-01",
        "ends_on": None,
        "anchor_day": 25,
        "analysis_group_id": None,
        "notes": None,
        "categories": [
            {
                "category_id": data["food"]["category_id"],
                "mode": "include",
                "include_descendants": True,
            }
        ],
        "tags": [{"tag_id": data["tag"]["tag_id"], "mode": "include"}],
    }
    payload.update(overrides)
    return payload


def test_budget_outcome_is_split_aware_and_recovery_aware(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_budget_data(client, headers)

    expense = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            **expense_payload(data, "2026-08-20", "1000"),
            "category_id": None,
            "tag_ids": [],
            "splits": [
                {
                    "original_amount": "600",
                    "category_id": data["food"]["category_id"],
                    "tag_ids": [data["tag"]["tag_id"]],
                    "is_base_cost": False,
                    "memo": "Mat",
                },
                {
                    "original_amount": "400",
                    "category_id": data["travel"]["category_id"],
                    "tag_ids": [],
                    "is_base_cost": False,
                    "memo": "Resa",
                },
            ],
        },
    )
    assert expense.status_code == 201, expense.text
    recovery = client.post(
        f"/api/v1/transactions/{expense.json()['transaction_id']}/refunds",
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
    assert recovery.status_code == 201, recovery.text
    missing_fx = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            **expense_payload(data, "2026-08-22", "100"),
            "description": "Mat med saknad valutakurs",
            "original_currency": "DKK",
        },
    )
    assert missing_fx.status_code == 201, missing_fx.text
    assert missing_fx.json()["converted_amount"] is None

    group = client.post(
        "/api/v1/analysis-groups",
        headers=headers,
        json={
            "name": "Mat hemma",
            "notes": None,
            "categories": [
                {
                    "category_id": data["food"]["category_id"],
                    "mode": "include",
                    "include_descendants": True,
                }
            ],
            "tags": [{"tag_id": data["tag"]["tag_id"], "mode": "include"}],
        },
    )
    assert group.status_code == 201, group.text
    budget = client.post(
        "/api/v1/budgets",
        headers=headers,
        json=budget_payload(
            data,
            categories=[],
            tags=[],
            analysis_group_id=group.json()["analysis_group_id"],
        ),
    )
    assert budget.status_code == 201, budget.text
    updated = client.patch(
        f"/api/v1/budgets/{budget.json()['budget_id']}",
        headers=headers,
        json=budget_payload(
            data,
            name="Matbudget uppdaterad",
            categories=[],
            tags=[],
            analysis_group_id=group.json()["analysis_group_id"],
        ),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Matbudget uppdaterad"

    outcome = client.get(
        f"/api/v1/budgets/{budget.json()['budget_id']}/outcome"
        "?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert outcome.status_code == 200, outcome.text
    assert outcome.json()["target_amount"] == "1000.0000"
    assert outcome.json()["actual_amount"] == "540.0000"
    assert outcome.json()["remaining_amount"] == "460.0000"
    assert outcome.json()["consumed_percent"] == "54.00"
    assert outcome.json()["matched_transaction_count"] == 2
    assert outcome.json()["missing_fx_count"] == 1

    rows = client.get(
        f"/api/v1/budgets/{budget.json()['budget_id']}/transactions"
        "?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert rows.status_code == 200
    assert {item["matched_amount"] for item in rows.json()} == {"600.0000", "-60.0000"}
    invalid_range = client.get(
        f"/api/v1/budgets/{budget.json()['budget_id']}/transactions"
        "?date_from=2026-08-31&date_to=2026-08-01"
    )
    assert invalid_range.status_code == 422

    overlapping = client.post(
        "/api/v1/budgets",
        headers=headers,
        json=budget_payload(data, name="Överlappande matbudget"),
    )
    assert overlapping.status_code == 201, overlapping.text
    updated_outcome = client.get(
        f"/api/v1/budgets/{budget.json()['budget_id']}/outcome"
        "?date_from=2026-08-01&date_to=2026-08-31"
    ).json()
    assert updated_outcome["overlapping_budget_ids"] == [overlapping.json()["budget_id"]]

    archived = client.post(
        f"/api/v1/budgets/{overlapping.json()['budget_id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert len(client.get("/api/v1/budgets").json()) == 1


def test_budget_rollover_starts_at_effective_date_and_inactive_ranges_are_empty(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_budget_data(client, headers)
    july_expense = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=expense_payload(data, "2026-07-20", "800"),
    )
    assert july_expense.status_code == 201, july_expense.text
    before_start = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=expense_payload(data, "2026-07-05", "500"),
    )
    assert before_start.status_code == 201, before_start.text

    budget = client.post(
        "/api/v1/budgets",
        headers=headers,
        json=budget_payload(
            data,
            name="Rullande matbudget",
            rollover_mode="rollover",
            starts_on="2026-07-10",
        ),
    )
    assert budget.status_code == 201, budget.text
    budget_id = budget.json()["budget_id"]
    august = client.get(
        f"/api/v1/budgets/{budget_id}/outcome?date_from=2026-08-01&date_to=2026-08-31"
    )
    assert august.status_code == 200, august.text
    assert august.json()["rollover_adjustment"] == "200.0000"
    assert august.json()["target_amount"] == "1200.0000"

    inactive = client.get(
        f"/api/v1/budgets/{budget_id}/outcome?date_from=2026-06-01&date_to=2026-06-30"
    )
    assert inactive.status_code == 200
    assert inactive.json()["target_amount"] == "0.0000"
    assert inactive.json()["actual_amount"] == "0.0000"


def test_budget_validation_preserves_base_currency_and_period_semantics(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_budget_data(client, headers)

    wrong_currency = client.post(
        "/api/v1/budgets", headers=headers, json=budget_payload(data, currency="EUR")
    )
    assert wrong_currency.status_code == 422
    assert wrong_currency.json()["error"]["code"] == "budget_currency_mismatch"

    invalid_custom = client.post(
        "/api/v1/budgets",
        headers=headers,
        json=budget_payload(
            data,
            name="Egen period",
            period_type="custom",
            ends_on="2026-12-31",
            rollover_mode="rollover",
        ),
    )
    assert invalid_custom.status_code == 422
