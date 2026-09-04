from __future__ import annotations

import json
import os
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = os.environ.get("COST_REVIEW_BASE_URL", "http://localhost:8080")
PASSWORD = "integration test password"


def api_client(environment: str):
    jar = CookieJar()
    return build_opener(HTTPCookieProcessor(jar)), jar, f"{BASE_URL}/api/{environment}/v1"


def call(opener, url: str, method: str = "GET", payload=None, csrf: str | None = None):
    headers = {}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode()
    if csrf:
        headers["X-CSRF-Token"] = csrf
    request = Request(url, data=data, headers=headers, method=method)
    with opener.open(request) as response:
        body = response.read()
        return response.status, json.loads(body) if body else None


def csrf_from(jar: CookieJar, name: str) -> str:
    for cookie in jar:
        if cookie.name == name:
            return cookie.value
    raise AssertionError(f"missing CSRF cookie {name}")


def setup_payload(username: str):
    return {
        "username": username,
        "password": PASSWORD,
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


def main() -> int:
    prod, prod_jar, prod_base = api_client("production")
    test, test_jar, test_base = api_client("test")

    _, prod_status = call(prod, f"{prod_base}/setup/status")
    _, test_status = call(test, f"{test_base}/setup/status")
    assert prod_status["data_plane_id"] != test_status["data_plane_id"]

    if prod_status["setup_required"]:
        call(prod, f"{prod_base}/setup", "POST", setup_payload("prod-owner"))
    else:
        call(
            prod,
            f"{prod_base}/auth/login",
            "POST",
            {"username": "prod-owner", "password": PASSWORD},
        )
    if test_status["setup_required"]:
        call(test, f"{test_base}/setup", "POST", setup_payload("test-owner"))
    else:
        call(
            test,
            f"{test_base}/auth/login",
            "POST",
            {"username": "test-owner", "password": PASSWORD},
        )

    prod_csrf = csrf_from(prod_jar, "cost_review_production_csrf")
    test_csrf = csrf_from(test_jar, "cost_review_test_csrf")
    call(prod, f"{prod_base}/settings", "PATCH", {"language": "en", "region": "GB"}, prod_csrf)
    account_payload = {
        "account_type": "current",
        "opening_balance": "1000.00",
        "opening_balance_date": "2026-08-28",
        "currency": "SEK",
    }
    _, prod_account = call(
        prod,
        f"{prod_base}/accounts",
        "POST",
        {**account_payload, "name": "Production isolation account"},
        prod_csrf,
    )
    _, test_account = call(
        test,
        f"{test_base}/accounts",
        "POST",
        {**account_payload, "name": "Test isolation account"},
        test_csrf,
    )
    _, prod_transfer_target = call(
        prod,
        f"{prod_base}/accounts",
        "POST",
        {
            **account_payload,
            "name": "Production transfer target",
            "account_type": "savings",
        },
        prod_csrf,
    )
    _, test_transfer_target = call(
        test,
        f"{test_base}/accounts",
        "POST",
        {
            **account_payload,
            "name": "Test transfer target",
            "account_type": "savings",
        },
        test_csrf,
    )
    _, prod_provider = call(
        prod,
        f"{prod_base}/providers",
        "POST",
        {"name": "Production isolation provider"},
        prod_csrf,
    )
    _, test_provider = call(
        test,
        f"{test_base}/providers",
        "POST",
        {"name": "Test isolation provider"},
        test_csrf,
    )
    transaction_payload = {
        "transaction_kind": "expense",
        "transaction_date": "2026-08-28",
        "posting_date": "2026-08-28",
        "original_amount": "125.50",
        "original_currency": "SEK",
    }
    _, prod_expense = call(
        prod,
        f"{prod_base}/transactions",
        "POST",
        {
            **transaction_payload,
            "account_id": prod_account["account_id"],
            "provider_id": prod_provider["provider_id"],
            "description": "Production isolation transaction",
        },
        prod_csrf,
    )
    _, test_expense = call(
        test,
        f"{test_base}/transactions",
        "POST",
        {
            **transaction_payload,
            "account_id": test_account["account_id"],
            "provider_id": test_provider["provider_id"],
            "description": "Test isolation transaction",
        },
        test_csrf,
    )
    recovery_payload = {
        "transaction_date": "2026-08-28",
        "posting_date": "2026-08-28",
        "original_amount": "25.50",
        "original_currency": "SEK",
    }
    call(
        prod,
        f"{prod_base}/transactions/{prod_expense['transaction_id']}/refunds",
        "POST",
        {
            **recovery_payload,
            "account_id": prod_account["account_id"],
            "description": "Production isolation refund",
        },
        prod_csrf,
    )
    call(
        test,
        f"{test_base}/transactions/{test_expense['transaction_id']}/reimbursements",
        "POST",
        {
            **recovery_payload,
            "account_id": test_account["account_id"],
            "description": "Test isolation reimbursement",
        },
        test_csrf,
    )
    transfer_payload = {
        "purpose": "savings",
        "transaction_date": "2026-08-28",
        "source_posting_date": "2026-08-28",
        "destination_posting_date": "2026-08-28",
        "source_amount": "75.00",
        "destination_amount": "75.00",
    }
    call(
        prod,
        f"{prod_base}/transfers",
        "POST",
        {
            **transfer_payload,
            "source_account_id": prod_account["account_id"],
            "destination_account_id": prod_transfer_target["account_id"],
            "description": "Production isolation transfer",
        },
        prod_csrf,
    )
    call(
        test,
        f"{test_base}/transfers",
        "POST",
        {
            **transfer_payload,
            "source_account_id": test_account["account_id"],
            "destination_account_id": test_transfer_target["account_id"],
            "description": "Test isolation transfer",
        },
        test_csrf,
    )
    snapshot_payload = {
        "valuation_date": "2026-08-28",
        "reported_balance": "825.00",
        "notes": "Isolation snapshot",
    }
    call(
        prod,
        f"{prod_base}/accounts/{prod_account['account_id']}/snapshots",
        "POST",
        snapshot_payload,
        prod_csrf,
    )
    call(
        test,
        f"{test_base}/accounts/{test_account['account_id']}/snapshots",
        "POST",
        snapshot_payload,
        test_csrf,
    )
    budget_payload = {
        "amount": "500.00",
        "currency": "SEK",
        "period_type": "calendar_month",
        "rollover_mode": "reset",
        "starts_on": "2026-08-01",
        "ends_on": None,
        "anchor_day": 25,
        "analysis_group_id": None,
        "notes": None,
        "categories": [],
        "tags": [],
    }
    call(
        prod,
        f"{prod_base}/budgets",
        "POST",
        {
            **budget_payload,
            "name": "Production isolation budget",
            "accounts": [{"account_id": prod_account["account_id"], "mode": "include"}],
            "providers": [
                {"provider_id": prod_provider["provider_id"], "mode": "include"}
            ],
        },
        prod_csrf,
    )
    call(
        test,
        f"{test_base}/budgets",
        "POST",
        {
            **budget_payload,
            "name": "Test isolation budget",
            "accounts": [{"account_id": test_account["account_id"], "mode": "include"}],
            "providers": [
                {"provider_id": test_provider["provider_id"], "mode": "include"}
            ],
        },
        test_csrf,
    )
    _, prod_accounts_before = call(prod, f"{prod_base}/accounts")
    _, test_accounts_before = call(test, f"{test_base}/accounts")
    assert any(
        account["name"] == "Production isolation account"
        for account in prod_accounts_before["items"]
    )
    assert not any(
        account["name"] == "Test isolation account"
        for account in prod_accounts_before["items"]
    )
    assert any(
        account["name"] == "Test isolation account"
        for account in test_accounts_before["items"]
    )
    assert not any(
        account["name"] == "Production isolation account"
        for account in test_accounts_before["items"]
    )
    _, prod_transactions_before = call(prod, f"{prod_base}/transactions")
    _, test_transactions_before = call(test, f"{test_base}/transactions")
    assert any(
        item["description"] == "Production isolation transaction"
        for item in prod_transactions_before["items"]
    )
    assert not any(
        item["description"] == "Test isolation transaction"
        for item in prod_transactions_before["items"]
    )
    assert any(
        item["description"] == "Production isolation refund"
        for item in prod_transactions_before["items"]
    )
    assert not any(
        item["description"] == "Test isolation reimbursement"
        for item in prod_transactions_before["items"]
    )
    assert any(
        item["description"] == "Test isolation transaction"
        for item in test_transactions_before["items"]
    )
    assert not any(
        item["description"] == "Production isolation transaction"
        for item in test_transactions_before["items"]
    )
    assert any(
        item["description"] == "Test isolation reimbursement"
        for item in test_transactions_before["items"]
    )
    assert not any(
        item["description"] == "Production isolation refund"
        for item in test_transactions_before["items"]
    )
    _, prod_transfers_before = call(prod, f"{prod_base}/transfers")
    _, test_transfers_before = call(test, f"{test_base}/transfers")
    assert any(
        item["description"] == "Production isolation transfer"
        for item in prod_transfers_before["items"]
    )
    assert not any(
        item["description"] == "Test isolation transfer"
        for item in prod_transfers_before["items"]
    )
    assert any(
        item["description"] == "Test isolation transfer"
        for item in test_transfers_before["items"]
    )
    assert not any(
        item["description"] == "Production isolation transfer"
        for item in test_transfers_before["items"]
    )
    _, prod_snapshots_before = call(
        prod, f"{prod_base}/accounts/{prod_account['account_id']}/snapshots"
    )
    _, test_snapshots_before = call(
        test, f"{test_base}/accounts/{test_account['account_id']}/snapshots"
    )
    assert len(prod_snapshots_before) == 1
    assert len(test_snapshots_before) == 1
    _, prod_budgets_before = call(prod, f"{prod_base}/budgets")
    _, test_budgets_before = call(test, f"{test_base}/budgets")
    assert [item["name"] for item in prod_budgets_before] == ["Production isolation budget"]
    assert [item["name"] for item in test_budgets_before] == ["Test isolation budget"]
    _, prod_before = call(prod, f"{prod_base}/auth/session")
    _, prod_environment_before = call(prod, f"{prod_base}/environment")

    _, reset = call(
        test,
        f"{test_base}/test/reset",
        "POST",
        {"confirmation": "DELETE ALL TEST DATA"},
        test_csrf,
    )
    assert reset["reset_generation"] >= 1

    _, test_accounts_after = call(test, f"{test_base}/accounts")
    _, prod_accounts_after = call(prod, f"{prod_base}/accounts")
    _, test_transactions_after = call(test, f"{test_base}/transactions")
    _, prod_transactions_after = call(prod, f"{prod_base}/transactions")
    _, test_transfers_after = call(test, f"{test_base}/transfers")
    _, prod_transfers_after = call(prod, f"{prod_base}/transfers")
    _, test_budgets_after = call(test, f"{test_base}/budgets")
    _, prod_budgets_after = call(prod, f"{prod_base}/budgets")
    _, prod_snapshots_after = call(
        prod, f"{prod_base}/accounts/{prod_account['account_id']}/snapshots"
    )
    assert test_accounts_after["total"] == 0
    assert test_transactions_after["total"] == 0
    assert test_transfers_after["total"] == 0
    assert test_budgets_after == []
    assert any(
        account["name"] == "Production isolation account"
        for account in prod_accounts_after["items"]
    )
    assert any(
        item["description"] == "Production isolation transaction"
        for item in prod_transactions_after["items"]
    )
    assert any(
        item["description"] == "Production isolation refund"
        for item in prod_transactions_after["items"]
    )
    assert any(
        item["description"] == "Production isolation transfer"
        for item in prod_transfers_after["items"]
    )
    assert len(prod_snapshots_after) == 1
    assert prod_snapshots_after[0]["reported_balance"] == "825.0000"
    assert [item["name"] for item in prod_budgets_after] == ["Production isolation budget"]

    _, prod_after = call(prod, f"{prod_base}/auth/session")
    _, prod_environment_after = call(prod, f"{prod_base}/environment")
    assert prod_after["settings"] == prod_before["settings"]
    assert prod_environment_after == prod_environment_before
    assert prod_environment_after["reset_generation"] == 0

    try:
        call(
            prod,
            f"{prod_base}/test/reset",
            "POST",
            {"confirmation": "DELETE ALL TEST DATA"},
            prod_csrf,
        )
    except HTTPError as error:
        assert error.code == 404
    else:
        raise AssertionError("Production unexpectedly exposed the test reset route")

    print("Production/Test HTTP isolation verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
