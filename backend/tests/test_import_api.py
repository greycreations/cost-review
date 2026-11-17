"""CSV/XLSX import: preview, staging, review, commit, duplicates and undo."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.config import Settings
from app.services import HOUSEHOLD_DATA_TABLES
from tests.test_transaction_api import authenticate, seed_master_data

EXPORT = (
    "Bokföringsdag;Transaktionsdag;Text;Belopp;Saldo\n"
    "2026-08-21;2026-08-20;ICA Kvantum;-425,35;10 000,00\n"
    "2026-08-21;2026-08-20;ICA Kvantum;-425,35;9 574,65\n"
    "2026-08-25;2026-08-25;Lön;32 000,00;41 574,65\n"
    "2026-08-26;felaktigt;Okänd;-10,00;41 564,65\n"
).encode("cp1252")

MAPPING = {
    "date_column": "Transaktionsdag",
    "posting_date_column": "Bokföringsdag",
    "description_column": "Text",
    "amount_column": "Belopp",
    "date_format": "%Y-%m-%d",
    "decimal_separator": ",",
}


def stage(
    client: TestClient,
    headers: dict[str, str],
    account_id: int,
    content: bytes = EXPORT,
    **options,
):
    return client.post(
        "/api/v1/imports",
        headers=headers,
        files={"file": ("bank.csv", content, "text/csv")},
        data={"options": json.dumps({"account_id": account_id, "mapping": MAPPING, **options})},
    )


def rows_by_status(client: TestClient, batch_id: int) -> dict[str, list[dict]]:
    items = client.get(f"/api/v1/imports/{batch_id}/rows").json()["items"]
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item["status"], []).append(item)
    return grouped


def test_preview_suggests_mapping_and_known_profiles(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)

    preview = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        files={"file": ("bank.csv", EXPORT, "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["row_count"] == 4
    assert body["delimiter"] == ";"
    assert body["suggested_mapping"]["amount_column"] == "Belopp"
    assert body["suggested_mapping"]["decimal_separator"] == ","
    assert body["profile_suggestions"] == []
    assert body["previous_imports"] == []

    staged = stage(
        client,
        headers,
        data["account"]["account_id"],
        save_profile_name="Vardagsbanken",
    )
    assert staged.status_code == 201, staged.text

    again = client.post(
        "/api/v1/imports/preview",
        headers=headers,
        files={"file": ("bank.csv", EXPORT, "text/csv")},
    ).json()
    assert again["profile_suggestions"][0]["name"] == "Vardagsbanken"
    assert again["profile_suggestions"][0]["confidence"] == 100
    assert again["previous_imports"][0]["import_batch_id"] == staged.json()["import_batch_id"]


def test_staging_never_touches_the_ledger_until_commit(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    staged = stage(client, headers, data["account"]["account_id"])
    assert staged.status_code == 201, staged.text
    batch = staged.json()
    assert batch["status"] == "staged"
    assert batch["status_counts"] == {
        "ready": 3,
        "duplicate": 0,
        "invalid": 1,
        "skipped": 0,
        "committed": 0,
    }
    assert client.get("/api/v1/transactions").json()["total"] == 0

    grouped = rows_by_status(client, batch["import_batch_id"])
    invalid = grouped["invalid"][0]
    assert invalid["errors"] == ["date_invalid"]
    assert invalid["raw"]["Transaktionsdag"] == "felaktigt"

    # Two identical purchases on one day are both kept: they are not duplicates.
    purchases = [row for row in grouped["ready"] if row["description"] == "ICA Kvantum"]
    assert len(purchases) == 2


def test_review_corrections_commit_and_category_assignment(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    batch_id = stage(client, headers, data["account"]["account_id"]).json()["import_batch_id"]
    grouped = rows_by_status(client, batch_id)
    invalid = grouped["invalid"][0]

    refused = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{invalid['import_row_id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "import_row_invalid"

    corrected = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{invalid['import_row_id']}",
        headers=headers,
        json={"transaction_date": "2026-08-26"},
    )
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "ready"
    assert corrected.json()["errors"] == []

    purchases = [row["import_row_id"] for row in grouped["ready"] if row["amount"].startswith("-")]
    bulk = client.post(
        f"/api/v1/imports/{batch_id}/rows/bulk",
        headers=headers,
        json={"import_row_ids": purchases, "category_id": data["expense"]["category_id"]},
    )
    assert bulk.json() == {"updated": 2}
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{invalid['import_row_id']}",
        headers=headers,
        json={"status": "skipped"},
    )

    committed = client.post(f"/api/v1/imports/{batch_id}/commit", headers=headers)
    assert committed.status_code == 200, committed.text
    assert committed.json()["status"] == "committed"
    assert committed.json()["status_counts"]["committed"] == 3
    assert committed.json()["status_counts"]["skipped"] == 1

    transactions = client.get("/api/v1/transactions").json()["items"]
    assert len(transactions) == 3
    assert {item["source_type"] for item in transactions} == {"import"}
    salary = next(item for item in transactions if item["description"] == "Lön")
    assert salary["transaction_kind"] == "income"
    assert salary["original_amount"] == "32000.0000"
    purchase = next(item for item in transactions if item["description"] == "ICA Kvantum")
    assert purchase["transaction_kind"] == "expense"
    assert purchase["posting_date"] == "2026-08-21"
    assert purchase["category_id"] == data["expense"]["category_id"]

    locked = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{invalid['import_row_id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert locked.status_code == 409


def test_a_category_of_the_wrong_kind_blocks_the_whole_commit(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    batch_id = stage(client, headers, data["account"]["account_id"]).json()["import_batch_id"]
    salary = next(
        row
        for row in rows_by_status(client, batch_id)["ready"]
        if row["description"] == "Lön"
    )
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{salary['import_row_id']}",
        headers=headers,
        json={"category_id": data["expense"]["category_id"]},
    )

    refused = client.post(f"/api/v1/imports/{batch_id}/commit", headers=headers)
    assert refused.status_code == 422
    assert refused.json()["error"]["code"] == "category_kind_mismatch"
    assert refused.json()["error"]["message"].startswith(f"Row {salary['row_number']}:")
    assert client.get("/api/v1/transactions").json()["total"] == 0
    assert client.get(f"/api/v1/imports/{batch_id}").json()["status"] == "staged"


def test_reimporting_the_same_export_flags_every_row_as_a_duplicate(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    account_id = data["account"]["account_id"]
    first = stage(client, headers, account_id).json()["import_batch_id"]
    assert client.post(f"/api/v1/imports/{first}/commit", headers=headers).status_code == 200

    second = stage(client, headers, account_id).json()
    assert second["status_counts"]["duplicate"] == 3
    assert second["status_counts"]["ready"] == 0
    duplicates = rows_by_status(client, second["import_batch_id"])["duplicate"]
    assert {row["duplicate_reason"] for row in duplicates} == {"previously_imported"}
    assert {row["duplicate_confidence"] for row in duplicates} == {100}
    assert all(row["duplicate_transaction_id"] for row in duplicates)

    nothing = client.post(
        f"/api/v1/imports/{second['import_batch_id']}/commit", headers=headers
    )
    assert nothing.status_code == 422
    assert nothing.json()["error"]["code"] == "import_nothing_ready"


def test_manual_entries_are_matched_as_likely_duplicates(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    manual = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": data["account"]["account_id"],
            "transaction_kind": "income",
            "transaction_date": "2026-08-24",
            "posting_date": "2026-08-24",
            "description": "Lön augusti",
            "original_amount": "32000",
            "original_currency": "SEK",
        },
    ).json()

    batch = stage(client, headers, data["account"]["account_id"]).json()
    duplicate = rows_by_status(client, batch["import_batch_id"])["duplicate"][0]
    assert duplicate["description"] == "Lön"
    assert duplicate["duplicate_reason"] == "matching_transaction"
    assert duplicate["duplicate_transaction_id"] == manual["transaction_id"]
    assert duplicate["duplicate_confidence"] == 65

    approved = client.patch(
        f"/api/v1/imports/{batch['import_batch_id']}/rows/{duplicate['import_row_id']}",
        headers=headers,
        json={"status": "ready"},
    )
    assert approved.json()["status"] == "ready"
    assert approved.json()["duplicate_transaction_id"] == manual["transaction_id"]


def test_undo_archives_exactly_the_imported_transactions(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    account_id = data["account"]["account_id"]
    batch_id = stage(client, headers, account_id).json()["import_batch_id"]
    client.post(f"/api/v1/imports/{batch_id}/commit", headers=headers)

    preview = client.get(f"/api/v1/imports/{batch_id}/undo-preview").json()
    assert preview["active_transaction_count"] == 3
    assert preview["expenses"] == "850.7000"
    assert preview["income"] == "32000.0000"
    assert preview["can_undo"] is True

    wrong = client.post(
        f"/api/v1/imports/{batch_id}/undo", headers=headers, json={"confirmation": "undo"}
    )
    assert wrong.status_code == 422
    undone = client.post(
        f"/api/v1/imports/{batch_id}/undo",
        headers=headers,
        json={"confirmation": "UNDO IMPORT"},
    )
    assert undone.status_code == 200, undone.text
    assert undone.json()["status"] == "undone"
    assert client.get("/api/v1/transactions").json()["total"] == 0
    archived = client.get("/api/v1/transactions?include_archived=true").json()["items"]
    assert {item["status"] for item in archived} == {"archived"}

    # After an undo the same export can be imported again without duplicate flags.
    again = stage(client, headers, account_id).json()
    assert again["status_counts"]["duplicate"] == 0

    audit = client.get("/api/v1/audit-events", params={"entity_type": "import_batch"}).json()
    assert [event["action"] for event in audit["items"]] == ["import_undone", "imported"]


def test_viewers_can_review_but_not_import(client: TestClient, settings: Settings) -> None:
    headers = authenticate(client, settings)
    data = seed_master_data(client, headers)
    batch_id = stage(client, headers, data["account"]["account_id"]).json()["import_batch_id"]
    client.post(
        "/api/v1/users",
        headers=headers,
        json={"username": "viewer", "password": "viewer account password", "role": "viewer"},
    )
    client.cookies.clear()
    client.post(
        "/api/v1/auth/login",
        json={"username": "viewer", "password": "viewer account password"},
    )
    viewer_headers = {"X-CSRF-Token": client.cookies.get(settings.csrf_cookie_name)}

    assert client.get(f"/api/v1/imports/{batch_id}/rows").status_code == 200
    denied = client.post(f"/api/v1/imports/{batch_id}/commit", headers=viewer_headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "read_only_member"


def test_household_data_tables_cover_every_table(client: TestClient) -> None:
    platform_tables = {
        "alembic_version",
        "environment_metadata",
        "users",
        "sessions",
        "app_settings",
    }
    database_tables = set(inspect(client.app.state.database.engine).get_table_names())
    assert database_tables - platform_tables == set(HOUSEHOLD_DATA_TABLES)
