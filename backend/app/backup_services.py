from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Literal
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from sqlalchemy import text
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.errors import ApiError
from app.models import EnvironmentMetadata

MAGIC = b"COSTREVIEW-BACKUP-1\n"
SALT_SIZE = 16
NONCE_SIZE = 12
BACKUP_SUFFIX = ".crbackup"
MAX_BACKUP_UPLOAD_BYTES = 5 * 1024 * 1024 * 1024
FILENAME_PATTERN = re.compile(
    r"^(?P<kind>manual|automatic|pre-restore)-"
    r"(?P<environment>production|test)-"
    r"(?P<timestamp>\d{8}T\d{6}Z)-[0-9a-f]{8}\.crbackup$"
)
BackupKind = Literal["manual", "automatic", "pre-restore"]


def create_backup(
    db: DbSession,
    settings: Settings,
    *,
    kind: BackupKind,
) -> dict[str, Any]:
    key = _backup_key(settings)
    settings.backup_root.mkdir(parents=True, exist_ok=True)
    settings.attachment_root.mkdir(parents=True, exist_ok=True)
    metadata = db.get(EnvironmentMetadata, 1)
    if metadata is None:
        raise RuntimeError("environment metadata is missing")
    schema_revision = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    created_at = datetime.now(UTC)
    filename = (
        f"{kind}-{settings.app_environment}-{created_at:%Y%m%dT%H%M%SZ}-"
        f"{uuid4().hex[:8]}{BACKUP_SUFFIX}"
    )
    destination = settings.backup_root / filename

    with tempfile.TemporaryDirectory(prefix="cost-review-backup-") as temporary:
        work_root = Path(temporary)
        database_dump = work_root / "database.dump"
        _run_pg_dump(settings, database_dump)
        checksums: dict[str, str] = {
            "database.dump": _sha256(database_dump),
        }
        attachment_files = _attachment_files(settings.attachment_root)
        for source in attachment_files:
            relative = source.relative_to(settings.attachment_root).as_posix()
            checksums[f"attachments/{relative}"] = _sha256(source)

        manifest = {
            "format": 1,
            "application": "Cost Review",
            "environment": settings.app_environment,
            "data_plane_id": str(metadata.data_plane_id),
            "created_at": created_at.isoformat(),
            "schema_revision": schema_revision,
            "kind": kind,
            "checksums": checksums,
        }
        archive = work_root / "payload.tar.gz"
        with tarfile.open(archive, "w:gz") as bundle:
            manifest_bytes = json.dumps(
                manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            manifest_info = tarfile.TarInfo("manifest.json")
            manifest_info.size = len(manifest_bytes)
            manifest_info.mtime = int(created_at.timestamp())
            bundle.addfile(manifest_info, io.BytesIO(manifest_bytes))
            bundle.add(database_dump, arcname="database.dump", recursive=False)
            for source in attachment_files:
                relative = source.relative_to(settings.attachment_root).as_posix()
                bundle.add(source, arcname=f"attachments/{relative}", recursive=False)

        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext = AESGCM(_derive_key(key, salt)).encrypt(
            nonce, archive.read_bytes(), MAGIC
        )
        temporary_destination = destination.with_suffix(destination.suffix + ".part")
        with temporary_destination.open("wb") as output:
            output.write(MAGIC)
            output.write(salt)
            output.write(nonce)
            output.write(ciphertext)
        temporary_destination.replace(destination)

    if kind == "automatic":
        enforce_retention(settings)
    return backup_values(destination)


def list_backups(settings: Settings) -> list[dict[str, Any]]:
    settings.backup_root.mkdir(parents=True, exist_ok=True)
    backups = [
        backup_values(path)
        for path in settings.backup_root.iterdir()
        if path.is_file() and FILENAME_PATTERN.fullmatch(path.name)
    ]
    return sorted(backups, key=lambda item: item["created_at"], reverse=True)


def validate_backup(settings: Settings, filename: str) -> dict[str, Any]:
    path = resolve_backup_path(settings, filename)
    return _validate_backup_path(settings, path)


def import_backup(
    settings: Settings,
    filename: str,
    source: BinaryIO,
) -> dict[str, Any]:
    match = FILENAME_PATTERN.fullmatch(filename)
    if match is None:
        raise ApiError(
            422,
            "backup_filename_invalid",
            "Select an original Cost Review .crbackup file.",
        )
    if match.group("environment") != settings.app_environment:
        raise ApiError(
            409,
            "backup_environment_mismatch",
            "The backup filename belongs to a different data plane.",
        )

    settings.backup_root.mkdir(parents=True, exist_ok=True)
    destination = settings.backup_root / filename
    if destination.exists():
        raise ApiError(409, "backup_already_exists", "This backup has already been imported.")

    temporary = settings.backup_root / f".{uuid4().hex}.upload"
    uploaded = 0
    try:
        with temporary.open("xb") as output:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                uploaded += len(chunk)
                if uploaded > MAX_BACKUP_UPLOAD_BYTES:
                    raise ApiError(
                        413,
                        "backup_upload_too_large",
                        "The backup exceeds the 5 GiB upload limit.",
                    )
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())

        validation = _validate_backup_path(settings, temporary, filename=filename)
        if validation["environment"] != settings.app_environment:
            raise ApiError(
                409,
                "backup_environment_mismatch",
                "The backup belongs to a different data plane and cannot be imported here.",
            )
        temporary.replace(destination)
        return validation
    finally:
        temporary.unlink(missing_ok=True)


def _validate_backup_path(
    settings: Settings,
    path: Path,
    *,
    filename: str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="cost-review-validate-") as temporary:
        extracted = Path(temporary)
        manifest = _decrypt_extract_validate(settings, path, extracted)
    return {
        "filename": filename or path.name,
        "environment": manifest["environment"],
        "data_plane_id": UUID(manifest["data_plane_id"]),
        "created_at": datetime.fromisoformat(manifest["created_at"]),
        "schema_revision": manifest["schema_revision"],
        "file_count": len(manifest["checksums"]),
        "valid": True,
    }


def restore_backup(settings: Settings, filename: str, confirmation: str) -> None:
    expected = (
        "RESTORE PRODUCTION"
        if settings.app_environment == "production"
        else "RESTORE DEMO/TEST"
    )
    if confirmation != expected:
        raise ApiError(
            422,
            "confirmation_mismatch",
            f"Type {expected} exactly to restore this data plane.",
        )
    path = resolve_backup_path(settings, filename)
    with tempfile.TemporaryDirectory(prefix="cost-review-restore-") as temporary:
        extracted = Path(temporary)
        manifest = _decrypt_extract_validate(settings, path, extracted)
        if manifest["environment"] != settings.app_environment:
            raise ApiError(
                409,
                "backup_environment_mismatch",
                "The backup belongs to a different data plane and cannot be restored here.",
            )
        _run_pg_restore(settings, extracted / "database.dump")
        _restore_attachments(settings.attachment_root, extracted / "attachments")
        _invalidate_restored_sessions(settings)


def enforce_retention(settings: Settings) -> None:
    automatic = [
        settings.backup_root / item["filename"]
        for item in list_backups(settings)
        if item["kind"] == "automatic"
    ]
    for expired in automatic[settings.backup_retention_count :]:
        expired.unlink()


def resolve_backup_path(settings: Settings, filename: str) -> Path:
    if not FILENAME_PATTERN.fullmatch(filename):
        raise ApiError(404, "backup_not_found", "Backup was not found.")
    root = settings.backup_root.resolve()
    path = (root / filename).resolve()
    if path.parent != root or not path.is_file():
        raise ApiError(404, "backup_not_found", "Backup was not found.")
    return path


def backup_values(path: Path) -> dict[str, Any]:
    match = FILENAME_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError("invalid Cost Review backup filename")
    return {
        "filename": path.name,
        "environment": match.group("environment"),
        "kind": match.group("kind").replace("pre-restore", "pre_restore"),
        "created_at": datetime.strptime(
            match.group("timestamp"), "%Y%m%dT%H%M%SZ"
        ).replace(
            tzinfo=UTC
        ),
        "size_bytes": path.stat().st_size,
    }


def _decrypt_extract_validate(
    settings: Settings, path: Path, destination: Path
) -> dict[str, Any]:
    payload = path.read_bytes()
    header_size = len(MAGIC) + SALT_SIZE + NONCE_SIZE
    if len(payload) <= header_size or not payload.startswith(MAGIC):
        raise ApiError(422, "backup_format_invalid", "Backup format is invalid.")
    salt_start = len(MAGIC)
    nonce_start = salt_start + SALT_SIZE
    ciphertext_start = nonce_start + NONCE_SIZE
    try:
        plaintext = AESGCM(
            _derive_key(_backup_key(settings), payload[salt_start:nonce_start])
        ).decrypt(
            payload[nonce_start:ciphertext_start],
            payload[ciphertext_start:],
            MAGIC,
        )
    except InvalidTag as error:
        raise ApiError(
            422,
            "backup_decryption_failed",
            "Backup integrity or encryption key validation failed.",
        ) from error
    try:
        with tarfile.open(fileobj=io.BytesIO(plaintext), mode="r:gz") as bundle:
            bundle.extractall(destination, filter="data")
        manifest = json.loads((destination / "manifest.json").read_text("utf-8"))
    except (OSError, tarfile.TarError, json.JSONDecodeError, KeyError) as error:
        raise ApiError(422, "backup_format_invalid", "Backup contents are invalid.") from error
    required = {
        "format",
        "application",
        "environment",
        "data_plane_id",
        "created_at",
        "schema_revision",
        "kind",
        "checksums",
    }
    if not isinstance(manifest, dict) or not required.issubset(manifest):
        raise ApiError(422, "backup_format_invalid", "Backup manifest is incomplete.")
    if manifest["format"] != 1 or manifest["application"] != "Cost Review":
        raise ApiError(422, "backup_format_invalid", "Backup format is not supported.")
    try:
        UUID(manifest["data_plane_id"])
        datetime.fromisoformat(manifest["created_at"])
        checksums = manifest["checksums"]
        if not isinstance(checksums, dict) or "database.dump" not in checksums:
            raise ValueError
        for relative, expected in checksums.items():
            candidate = (destination / relative).resolve()
            if destination.resolve() not in candidate.parents or _sha256(candidate) != expected:
                raise ValueError
    except (OSError, TypeError, ValueError) as error:
        raise ApiError(
            422, "backup_integrity_failed", "Backup checksum validation failed."
        ) from error
    return manifest


def _run_pg_dump(settings: Settings, destination: Path) -> None:
    command = [
        "pg_dump",
        "--host",
        settings.db_host,
        "--port",
        str(settings.db_port),
        "--username",
        settings.db_user,
        "--dbname",
        settings.db_name,
        "--format=custom",
        "--no-owner",
        "--no-privileges",
        "--file",
        str(destination),
    ]
    _run_postgres_command(command, settings)


def _run_pg_restore(settings: Settings, source: Path) -> None:
    command = [
        "pg_restore",
        "--host",
        settings.db_host,
        "--port",
        str(settings.db_port),
        "--username",
        settings.db_user,
        "--dbname",
        settings.db_name,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--single-transaction",
        str(source),
    ]
    _run_postgres_command(command, settings)


def _run_postgres_command(command: list[str], settings: Settings) -> None:
    environment = os.environ.copy()
    environment["PGPASSWORD"] = settings.db_password
    try:
        subprocess.run(
            command,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise ApiError(
            503,
            "backup_database_command_failed",
            "The PostgreSQL backup or restore command failed.",
        ) from error


def _invalidate_restored_sessions(settings: Settings) -> None:
    command = [
        "psql",
        "--host",
        settings.db_host,
        "--port",
        str(settings.db_port),
        "--username",
        settings.db_user,
        "--dbname",
        settings.db_name,
        "--command",
        "DELETE FROM sessions",
    ]
    _run_postgres_command(command, settings)


def _restore_attachments(destination: Path, source: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in destination.iterdir():
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink()
    if source.exists():
        for child in source.iterdir():
            target = destination / child.name
            if child.is_dir():
                shutil.copytree(child, target)
            else:
                shutil.copy2(child, target)


def _attachment_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    )


def _backup_key(settings: Settings) -> bytes:
    value = settings.backup_encryption_key.encode("utf-8")
    if len(value) < 32:
        raise ApiError(
            503,
            "backup_key_not_configured",
            "A backup encryption key of at least 32 bytes must be configured.",
        )
    return value


def _derive_key(passphrase: bytes, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
