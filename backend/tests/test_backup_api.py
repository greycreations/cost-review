from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import backup_services
from app.config import Settings

SETUP_PAYLOAD = {
    "username": "backup-owner",
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
    assert client.post("/api/v1/setup", json=SETUP_PAYLOAD).status_code == 201
    csrf = client.cookies.get(settings.csrf_cookie_name)
    assert csrf
    return {"X-CSRF-Token": csrf}


def test_backup_api_encrypts_lists_downloads_and_detects_tampering(
    client: TestClient,
    settings: Settings,
    tmp_path: Path,
    monkeypatch,
) -> None:
    headers = authenticate(client, settings)
    backup_root = tmp_path / "backups"
    attachment_root = tmp_path / "attachments"
    attachment_root.mkdir()
    (attachment_root / "receipt.txt").write_text("attachment evidence", encoding="utf-8")
    original_values = (
        settings.backup_root,
        settings.attachment_root,
        settings.backup_encryption_key,
    )
    settings.backup_root = backup_root
    settings.attachment_root = attachment_root
    settings.backup_encryption_key = "test-only-backup-key-that-is-long-enough"

    def fake_dump(_: Settings, destination: Path) -> None:
        destination.write_bytes(b"postgres-custom-dump-placeholder")

    monkeypatch.setattr(backup_services, "_run_pg_dump", fake_dump)
    try:
        created = client.post("/api/v1/backups", headers=headers)
        assert created.status_code == 201, created.text
        item = created.json()
        assert item["environment"] == "test"
        assert item["kind"] == "manual"
        assert item["size_bytes"] > 0

        listed = client.get("/api/v1/backups")
        assert listed.status_code == 200
        assert listed.json() == [item]

        validated = client.post(
            f"/api/v1/backups/{item['filename']}/validate", headers=headers
        )
        assert validated.status_code == 200, validated.text
        assert validated.json()["valid"] is True
        assert validated.json()["file_count"] == 2

        downloaded = client.get(f"/api/v1/backups/{item['filename']}/download")
        assert downloaded.status_code == 200
        assert downloaded.content.startswith(backup_services.MAGIC)

        path = backup_root / item["filename"]
        payload = bytearray(path.read_bytes())
        payload[-1] ^= 1
        path.write_bytes(payload)
        invalid = client.post(
            f"/api/v1/backups/{item['filename']}/validate", headers=headers
        )
        assert invalid.status_code == 422
        assert invalid.json()["error"]["code"] == "backup_decryption_failed"
    finally:
        (
            settings.backup_root,
            settings.attachment_root,
            settings.backup_encryption_key,
        ) = original_values


def test_backup_requires_a_separate_configured_encryption_key(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    headers = authenticate(client, settings)
    original_values = (settings.backup_root, settings.backup_encryption_key)
    settings.backup_root = tmp_path
    settings.backup_encryption_key = ""
    try:
        response = client.post("/api/v1/backups", headers=headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "backup_key_not_configured"
    finally:
        settings.backup_root, settings.backup_encryption_key = original_values
