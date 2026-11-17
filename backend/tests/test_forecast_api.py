from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from test_transaction_api import authenticate, seed_master_data, transaction_payload

from app.config import Settings
from app.forecast_services import month_expense_forecast


def test_month_forecast_uses_remaining_net_expenses_and_budget_selection(
    client: TestClient,
    settings: Settings,
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    for day, amount in [
        ("2026-08-20", "100"),
        ("2026-09-20", "200"),
        ("2026-10-20", "300"),
        ("2026-11-10", "50"),
        ("2026-11-20", "1000"),
    ]:
        response = client.post(
            "/api/v1/transactions",
            headers=headers,
            json=transaction_payload(
                data,
                transaction_date=day,
                posting_date=day,
                original_amount=amount,
            ),
        )
        assert response.status_code == 201, response.text

    budget = client.post(
        "/api/v1/budgets",
        headers=headers,
        json={
            "name": "Mat",
            "amount": "220",
            "currency": "SEK",
            "starts_on": "2026-08-01",
            "categories": [{"category_id": data["expense"]["category_id"]}],
        },
    )
    assert budget.status_code == 201, budget.text

    with client.app.state.database.session() as db:
        forecast = month_expense_forecast(db, date(2026, 11, 15), "SEK")
        sparse = month_expense_forecast(db, date(2026, 10, 15), "SEK")
    assert forecast["actual_expenses"] == Decimal("50")
    assert forecast["forecast_expenses"] == Decimal("250")
    assert forecast["history_month_count"] == 3
    assert forecast["budget_risks"] == [
        {
            "budget_id": budget.json()["budget_id"],
            "name": "Mat",
            "actual_amount": Decimal("50"),
            "target_amount": Decimal("220"),
            "forecast_amount": Decimal("250"),
            "overrun": Decimal("30"),
        }
    ]
    assert sparse["forecast_expenses"] is None
    assert sparse["budget_risks"] == []

    response = client.get("/api/v1/transactions/month-forecast")
    assert response.status_code == 200, response.text

    missing = client.post(
        "/api/v1/transactions",
        headers=headers,
        json=transaction_payload(
            data,
            transaction_date="2026-11-11",
            posting_date="2026-11-11",
            original_currency="EUR",
        ),
    )
    assert missing.status_code == 201, missing.text
    with client.app.state.database.session() as db:
        incomplete = month_expense_forecast(db, date(2026, 11, 15), "SEK")
    assert incomplete["actual_expenses"] == Decimal("50")
    assert incomplete["forecast_expenses"] is None
    assert incomplete["missing_fx_count"] == 1
    assert incomplete["budget_risks"] == []
