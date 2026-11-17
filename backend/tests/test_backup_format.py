"""Backup format 2: chunked authenticated encryption with constant memory use."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import backup_services
from app.errors import ApiError

KEY = b"test-only-backup-key-that-is-long-enough"
CHUNK = 64


@pytest.fixture
def small_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(backup_services, "CHUNK_SIZE", CHUNK)


def encrypt(tmp_path: Path, payload: bytes) -> Path:
    source = tmp_path / "payload.bin"
    source.write_bytes(payload)
    encrypted = tmp_path / "payload.crbackup"
    backup_services._encrypt_stream(KEY, source, encrypted)
    return encrypted


def decrypt(tmp_path: Path, encrypted: Path) -> bytes:
    target = tmp_path / "restored.bin"
    backup_services._decrypt_to_file(KEY, encrypted, target)
    return target.read_bytes()


def header_size() -> int:
    return (
        len(backup_services.MAGIC_V2)
        + backup_services.SALT_SIZE
        + backup_services.NONCE_PREFIX_SIZE
        + 4
    )


@pytest.mark.parametrize("size", [0, 1, CHUNK - 1, CHUNK, CHUNK + 1, CHUNK * 5 + 17])
def test_round_trip_across_chunk_boundaries(
    tmp_path: Path, small_chunks: None, size: int
) -> None:
    payload = os.urandom(size)
    encrypted = encrypt(tmp_path, payload)

    assert encrypted.read_bytes().startswith(backup_services.MAGIC_V2)
    assert decrypt(tmp_path, encrypted) == payload


def test_truncating_whole_chunks_is_detected(tmp_path: Path, small_chunks: None) -> None:
    encrypted = encrypt(tmp_path, os.urandom(CHUNK * 3))
    sealed = CHUNK + backup_services.TAG_SIZE
    data = encrypted.read_bytes()
    encrypted.write_bytes(data[: header_size() + 2 * sealed])

    with pytest.raises(ApiError) as error:
        decrypt(tmp_path, encrypted)
    assert error.value.code == "backup_decryption_failed"


def test_reordered_chunks_are_detected(tmp_path: Path, small_chunks: None) -> None:
    encrypted = encrypt(tmp_path, os.urandom(CHUNK * 3))
    sealed = CHUNK + backup_services.TAG_SIZE
    data = encrypted.read_bytes()
    start = header_size()
    first, second = data[start : start + sealed], data[start + sealed : start + 2 * sealed]
    encrypted.write_bytes(data[:start] + second + first + data[start + 2 * sealed :])

    with pytest.raises(ApiError) as error:
        decrypt(tmp_path, encrypted)
    assert error.value.code == "backup_decryption_failed"


def test_wrong_key_is_rejected(tmp_path: Path) -> None:
    encrypted = encrypt(tmp_path, b"household ledger")
    with pytest.raises(ApiError) as error:
        backup_services._decrypt_to_file(
            b"another-installation-key-also-long-enough", encrypted, tmp_path / "x"
        )
    assert error.value.code == "backup_decryption_failed"


def test_format_1_archives_remain_readable(tmp_path: Path) -> None:
    payload = b"archive written by Cost Review 0.8"
    salt = os.urandom(backup_services.SALT_SIZE)
    nonce = os.urandom(backup_services.NONCE_SIZE)
    ciphertext = AESGCM(backup_services._derive_key(KEY, salt)).encrypt(
        nonce, payload, backup_services.MAGIC
    )
    legacy = tmp_path / "legacy.crbackup"
    legacy.write_bytes(backup_services.MAGIC + salt + nonce + ciphertext)

    assert decrypt(tmp_path, legacy) == payload


def test_unknown_format_is_rejected(tmp_path: Path) -> None:
    unknown = tmp_path / "unknown.crbackup"
    unknown.write_bytes(b"NOT-A-COST-REVIEW-BACKUP")
    with pytest.raises(ApiError) as error:
        decrypt(tmp_path, unknown)
    assert error.value.code == "backup_format_invalid"


def test_restore_refuses_a_schema_from_a_newer_release() -> None:
    known = backup_services.known_schema_revisions()
    assert "20260828_0001" in known
    assert "20261116_0018" in known
    backup_services.ensure_schema_supported("20260912_0017")

    with pytest.raises(ApiError) as error:
        backup_services.ensure_schema_supported("20991231_9999")
    assert error.value.code == "backup_schema_newer"
