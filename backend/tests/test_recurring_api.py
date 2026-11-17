"""Recurring definitions, Expected occurrences and confirmation as Actual events."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.config import Settings
from app.models import RecurringDefinition, RecurringVersion
from app.recurring_services import due_dates, version_on
from tests.test_transaction_api import authenticate, seed_master_data

AUGUST = "date_from=2026-08-01&date_to=2026-08-31"


def definition(**values) -> RecurringDefinition:
    model = RecurringDefinition(
        name="Hyra",
        account_id=1,
        transaction_kind="expense",
        currency="SEK",
        frequency=values.pop("frequency", "monthly"),
        interval_count=values.pop("interval_count", 1),
        start_date=values.pop("start_date", date(2026, 1, 31)),
        end_date=values.pop("end_date", None),
        tolerance_percent=Decimal("10"),
    )
    model.versions = [
        RecurringVersion(
            effective_from=model.start_date, amount=Decimal("100"), amount_type="fixed"
        )
    ]
    return model


def test_monthly_schedule_keeps_the_anchor_day_or_the_last_day() -> None:
    dates = due_dates(definition(), date(2026, 1, 1), date(2026, 5, 31))
    assert dates == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]
    leap = due_dates(definition(start_date=date(2028, 1, 31)), date(2028, 2, 1), date(2028, 2, 29))
    assert leap == [date(2028, 2, 29)]


def test_quarterly_weekly_and_end_dates() -> None:
    quarterly = definition(frequency="quarterly", start_date=date(2026, 1, 15))
    assert due_dates(quarterly, date(2026, 5, 1), date(2027, 1, 31)) == [
        date(2026, 7, 15),
        date(2026, 10, 15),
        date(2027, 1, 15),
    ]
    fortnightly = definition(frequency="weekly", interval_count=2, start_date=date(2026, 8, 3))
    assert due_dates(fortnightly, date(2026, 8, 10), date(2026, 9, 1)) == [
        date(2026, 8, 17),
        date(2026, 8, 31),
    ]
    ending = definition(start_date=date(2026, 1, 10), end_date=date(2026, 3, 9))
    assert due_dates(ending, date(2026, 1, 1), date(2026, 12, 31)) == [
        date(2026, 1, 10),
        date(2026, 2, 10),
    ]


def test_amount_versions_apply_from_their_effective_date() -> None:
    model = definition(start_date=date(2026, 1, 1))
    model.versions.append(
        RecurringVersion(
            effective_from=date(2026, 7, 1), amount=Decimal("120"), amount_type="fixed"
        )
    )
    assert version_on(model, date(2026, 6, 1)).amount == Decimal("100")
    assert version_on(model, date(2026, 7, 1)).amount == Decimal("120")


def create_rent(client: TestClient, headers: dict[str, str], data: dict, **overrides):
    payload = {
        "name": "Hyra",
        "account_id": data["account"]["account_id"],
        "category_id": data["expense"]["category_id"],
        "transaction_kind": "expense",
        "amount": "9500",
        "frequency": "monthly",
        "start_date": "2026-06-25",
    }
    payload.update(overrides)
    response = client.post("/api/v1/recurring", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_expected_occurrences_never_change_actual_totals(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    rent = create_rent(client, headers, data)
    assert rent["currency"] == "SEK"
    assert rent["versions"] == [
        {"effective_from": "2026-06-25", "amount": "9500.0000", "amount_type": "fixed"}
    ]

    expected = client.get(f"/api/v1/recurring/expected?{AUGUST}").json()
    assert [(item["due_date"], item["expected_amount"]) for item in expected] == [
        ("2026-08-25", "9500.0000")
    ]
    assert expected[0]["status"] in {"expected", "overdue"}
    summary = client.get(f"/api/v1/transactions/summary?{AUGUST}").json()
    assert summary["expenses"] == "0.0000"
    assert client.get("/api/v1/transactions").json()["total"] == 0


def test_confirming_records_an_actual_event_and_measures_deviation(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    electricity = create_rent(
        client,
        headers,
        data,
        name="El",
        amount="800",
        amount_type="variable",
        tolerance_percent="10",
    )
    item_id = electricity["recurring_definition_id"]

    confirmed = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-25/confirm",
        headers=headers,
        json={"amount": "1000"},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["deviation_percent"] == "25.0000"
    assert body["outside_tolerance"] is True

    transaction = client.get(f"/api/v1/transactions/{body['transaction_id']}").json()
    assert transaction["source_type"] == "recurring"
    assert transaction["original_amount"] == "1000.0000"
    assert transaction["category_id"] == data["expense"]["category_id"]
    assert transaction["transaction_date"] == "2026-08-25"
    summary = client.get(f"/api/v1/transactions/summary?{AUGUST}").json()
    assert summary["expenses"] == "1000.0000"

    again = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-25/confirm",
        headers=headers,
        json={},
    )
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "occurrence_already_decided"
    assert client.get("/api/v1/transactions").json()["total"] == 1

    not_due = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-26/confirm",
        headers=headers,
        json={},
    )
    assert not_due.status_code == 422
    assert not_due.json()["error"]["code"] == "not_a_due_date"


def test_existing_transactions_are_offered_and_linked_as_candidates(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    rent = create_rent(client, headers, data)
    paid = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": data["account"]["account_id"],
            "transaction_kind": "expense",
            "transaction_date": "2026-08-24",
            "posting_date": "2026-08-24",
            "description": "Hyra augusti",
            "original_amount": "9500",
            "original_currency": "SEK",
        },
    ).json()

    expected = client.get(f"/api/v1/recurring/expected?{AUGUST}").json()[0]
    assert expected["candidates"][0]["transaction_id"] == paid["transaction_id"]
    assert expected["candidates"][0]["confidence"] >= 90

    linked = client.post(
        f"/api/v1/recurring/{rent['recurring_definition_id']}/occurrences/2026-08-25/confirm",
        headers=headers,
        json={"transaction_id": paid["transaction_id"]},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["transaction_id"] == paid["transaction_id"]
    assert linked.json()["deviation_percent"] == "0.0000"
    assert client.get("/api/v1/transactions").json()["total"] == 1

    after = client.get(f"/api/v1/recurring/expected?{AUGUST}").json()[0]
    assert after["status"] == "confirmed"
    assert after["candidates"] == []


def test_skip_reopen_amount_change_and_viewer_access(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    rent = create_rent(client, headers, data)
    item_id = rent["recurring_definition_id"]

    skipped = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-25/skip", headers=headers
    )
    assert skipped.json()["status"] == "skipped"
    reopened = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-25/reopen", headers=headers
    )
    assert reopened.status_code == 204
    assert client.get(f"/api/v1/recurring/expected?{AUGUST}").json()[0]["status"] != "skipped"

    raised = client.post(
        f"/api/v1/recurring/{item_id}/amount",
        headers=headers,
        json={"effective_from": "2026-09-01", "amount": "9900"},
    )
    assert raised.status_code == 200
    autumn = client.get(
        "/api/v1/recurring/expected?date_from=2026-08-01&date_to=2026-09-30"
    ).json()
    assert [item["expected_amount"] for item in autumn] == ["9500.0000", "9900.0000"]

    wrong_kind = client.post(
        "/api/v1/recurring",
        headers=headers,
        json={
            "name": "Lön",
            "account_id": data["account"]["account_id"],
            "category_id": data["expense"]["category_id"],
            "transaction_kind": "income",
            "amount": "32000",
            "start_date": "2026-08-25",
        },
    )
    assert wrong_kind.status_code == 422
    assert wrong_kind.json()["error"]["code"] == "category_kind_mismatch"

    client.post(
        "/api/v1/users",
        headers=headers,
        json={"username": "viewer", "password": "viewer account password", "role": "viewer"},
    )
    client.cookies.clear()
    client.post(
        "/api/v1/auth/login", json={"username": "viewer", "password": "viewer account password"}
    )
    viewer_headers = {"X-CSRF-Token": client.cookies.get(settings.csrf_cookie_name)}
    assert client.get(f"/api/v1/recurring/expected?{AUGUST}").status_code == 200
    denied = client.post(
        f"/api/v1/recurring/{item_id}/occurrences/2026-08-25/skip", headers=viewer_headers
    )
    assert denied.status_code == 403
