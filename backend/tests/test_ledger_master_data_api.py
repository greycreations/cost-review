from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import Settings

SETUP_PAYLOAD = {
    "username": "ledger-owner",
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


def test_account_crud_preserves_opening_balance_and_uses_archive_restore(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    created = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Lönekonto",
            "account_type": "current",
            "opening_balance": "12500.25",
            "opening_balance_date": "2026-01-01",
            "currency": "sek",
            "interest_rate": "0.15",
            "is_locked": False,
        },
    )
    assert created.status_code == 201
    account = created.json()
    assert account["currency"] == "SEK"
    assert account["opening_balance"] == "12500.2500"
    assert account["status"] == "active"

    updated = client.patch(
        f"/api/v1/accounts/{account['account_id']}",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "is_locked": True,
            "lock_start_date": "2026-02-01",
            "lock_end_date": "2026-12-31",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Vardagskonto"

    invalid_dates = client.patch(
        f"/api/v1/accounts/{account['account_id']}",
        headers=headers,
        json={"lock_start_date": None, "lock_end_date": "2026-12-31"},
    )
    assert invalid_dates.status_code == 422
    assert invalid_dates.json()["error"]["code"] == "invalid_lock_dates"

    archived = client.post(f"/api/v1/accounts/{account['account_id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert client.get("/api/v1/accounts").json()["total"] == 0
    assert client.get("/api/v1/accounts?include_archived=true").json()["total"] == 1

    restored = client.post(f"/api/v1/accounts/{account['account_id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"


def test_category_hierarchy_is_arbitrary_depth_and_cycle_safe(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    root = _create_category(client, headers, "Boende")
    child = _create_category(client, headers, "Bostad", root["category_id"])
    grandchild = _create_category(client, headers, "El", child["category_id"])

    cycle = client.patch(
        f"/api/v1/categories/{root['category_id']}",
        headers=headers,
        json={"parent_category_id": grandchild["category_id"]},
    )
    assert cycle.status_code == 409
    assert cycle.json()["error"]["code"] == "category_hierarchy_cycle"

    blocked_archive = client.post(
        f"/api/v1/categories/{root['category_id']}/archive", headers=headers
    )
    assert blocked_archive.status_code == 409
    assert blocked_archive.json()["error"]["code"] == "category_has_active_children"

    with (
        pytest.raises(IntegrityError),
        client.app.state.database.engine.begin() as connection,
    ):
        connection.execute(
            text(
                "UPDATE categories SET parent_category_id = :parent_id "
                "WHERE category_id = :category_id"
            ),
            {
                "parent_id": grandchild["category_id"],
                "category_id": root["category_id"],
            },
        )

    for category in (grandchild, child, root):
        archived = client.post(
            f"/api/v1/categories/{category['category_id']}/archive", headers=headers
        )
        assert archived.status_code == 200

    blocked_restore = client.post(
        f"/api/v1/categories/{child['category_id']}/restore", headers=headers
    )
    assert blocked_restore.status_code == 409
    assert blocked_restore.json()["error"]["code"] == "archived_dependency"

    for category in (root, child, grandchild):
        restored = client.post(
            f"/api/v1/categories/{category['category_id']}/restore", headers=headers
        )
        assert restored.status_code == 200


def test_provider_aliases_and_links_are_canonical_and_non_destructive(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    first = _create_provider(client, headers, "ICA Sverige")
    second = _create_provider(client, headers, "ICA Banken")

    alias = client.post(
        f"/api/v1/providers/{first['provider_id']}/aliases",
        headers=headers,
        json={"alias": " ICA MAXI "},
    )
    assert alias.status_code == 201

    conflict = client.post(
        f"/api/v1/providers/{second['provider_id']}/aliases",
        headers=headers,
        json={"alias": "ica maxi"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "provider_alias_exists"

    link = client.post(
        "/api/v1/provider-links",
        headers=headers,
        json={
            "first_provider_id": second["provider_id"],
            "second_provider_id": first["provider_id"],
            "label": "same group",
        },
    )
    assert link.status_code == 201
    assert link.json()["lower_provider_id"] == min(first["provider_id"], second["provider_id"])
    assert link.json()["higher_provider_id"] == max(first["provider_id"], second["provider_id"])

    duplicate = client.post(
        "/api/v1/provider-links",
        headers=headers,
        json={
            "first_provider_id": first["provider_id"],
            "second_provider_id": second["provider_id"],
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "provider_link_exists"


def test_tags_parties_and_test_reset_obey_lifecycle_and_environment_contract(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    tag = client.post(
        "/api/v1/tags", headers=headers, json={"name": "Semester", "color": "#4A67D6"}
    )
    assert tag.status_code == 201
    party = client.post(
        "/api/v1/sharing-parties",
        headers=headers,
        json={"name": "Jag", "is_self": True},
    )
    assert party.status_code == 201

    other_self = client.post(
        "/api/v1/sharing-parties",
        headers=headers,
        json={"name": "Också jag", "is_self": True},
    )
    assert other_self.status_code == 409
    assert other_self.json()["error"]["code"] == "active_self_exists"

    reset = client.post(
        "/api/v1/test/reset",
        headers=headers,
        json={"confirmation": "DELETE ALL TEST DATA"},
    )
    assert reset.status_code == 200
    assert client.get("/api/v1/tags").json()["total"] == 0
    assert client.get("/api/v1/sharing-parties").json()["total"] == 0
    assert client.get("/api/v1/auth/session").status_code == 200


def test_tag_merge_retargets_references_deduplicates_and_preserves_audit(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    source = client.post("/api/v1/tags", headers=headers, json={"name": "Mat"}).json()
    target = client.post("/api/v1/tags", headers=headers, json={"name": "Livsmedel"}).json()
    account = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "name": "Vardagskonto",
            "account_type": "current",
            "opening_balance": "0",
            "opening_balance_date": "2026-09-01",
            "currency": "SEK",
        },
    ).json()
    transaction = client.post(
        "/api/v1/transactions",
        headers=headers,
        json={
            "account_id": account["account_id"],
            "transaction_kind": "expense",
            "transaction_date": "2026-09-02",
            "posting_date": "2026-09-02",
            "description": "Matbutik",
            "original_amount": "100",
            "original_currency": "SEK",
            "tag_ids": [source["tag_id"], target["tag_id"]],
        },
    ).json()
    group = client.post(
        "/api/v1/analysis-groups",
        headers=headers,
        json={
            "name": "Matgrupp",
            "tags": [
                {"tag_id": source["tag_id"], "mode": "include"},
                {"tag_id": target["tag_id"], "mode": "include"},
            ],
        },
    )
    assert group.status_code == 201, group.text

    merged = client.post(
        f"/api/v1/tags/{source['tag_id']}/merge",
        headers=headers,
        json={"target_tag_id": target["tag_id"], "confirmation": "MERGE TAG"},
    )
    assert merged.status_code == 200, merged.text
    assert merged.json()["tag_id"] == target["tag_id"]
    assert client.get(f"/api/v1/tags/{source['tag_id']}").json()["status"] == "archived"
    reloaded = client.get(f"/api/v1/transactions/{transaction['transaction_id']}").json()
    assert reloaded["tag_ids"] == [target["tag_id"]]
    groups = client.get("/api/v1/analysis-groups").json()
    assert groups[0]["tags"] == [{"tag_id": target["tag_id"], "mode": "include"}]
    audit = client.get(
        f"/api/v1/audit-events?entity_type=tag&entity_id={source['tag_id']}"
    ).json()
    assert any(
        event["action"] == "updated"
        and event["changes"].get("target_tag_id") == target["tag_id"]
        for event in audit["items"]
    )


def test_tag_merge_stops_on_conflicting_analysis_selection(
    client: TestClient, settings: Settings
) -> None:
    headers = authenticate(client, settings)
    source = client.post("/api/v1/tags", headers=headers, json={"name": "Källa"}).json()
    target = client.post("/api/v1/tags", headers=headers, json={"name": "Mål"}).json()
    group = client.post(
        "/api/v1/analysis-groups",
        headers=headers,
        json={
            "name": "Konflikt",
            "tags": [
                {"tag_id": source["tag_id"], "mode": "include"},
                {"tag_id": target["tag_id"], "mode": "exclude"},
            ],
        },
    )
    assert group.status_code == 201, group.text

    conflict = client.post(
        f"/api/v1/tags/{source['tag_id']}/merge",
        headers=headers,
        json={"target_tag_id": target["tag_id"], "confirmation": "MERGE TAG"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "tag_merge_selection_conflict"
    assert conflict.json()["error"]["details"] == [
        {"resource": "analysis_group", "id": group.json()["analysis_group_id"]}
    ]
    assert client.get(f"/api/v1/tags/{source['tag_id']}").json()["status"] == "active"


def _create_category(
    client: TestClient, headers: dict[str, str], name: str, parent_id: int | None = None
) -> dict:
    response = client.post(
        "/api/v1/categories",
        headers=headers,
        json={
            "name": name,
            "category_kind": "expense",
            "parent_category_id": parent_id,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_provider(client: TestClient, headers: dict[str, str], name: str) -> dict:
    response = client.post("/api/v1/providers", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()
