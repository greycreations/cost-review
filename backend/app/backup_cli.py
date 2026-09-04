from __future__ import annotations

import argparse
import sys
import time

from app.backup_services import create_backup, restore_backup, validate_backup
from app.config import get_settings
from app.database import Database, ensure_environment_identity
from app.errors import ApiError


def main() -> int:
    parser = argparse.ArgumentParser(description="Cost Review backup and offline restore")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create")
    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("filename")
    restore_parser = commands.add_parser("restore")
    restore_parser.add_argument("filename")
    restore_parser.add_argument("--confirmation", required=True)
    commands.add_parser("schedule")
    arguments = parser.parse_args()
    settings = get_settings()

    try:
        if arguments.command == "restore":
            validate_backup(settings, arguments.filename)
            database = Database(settings)
            ensure_environment_identity(database, settings)
            with database.session() as db:
                safety_backup = create_backup(db, settings, kind="pre-restore")
            database.dispose()
            print(
                f"Created pre-restore safety backup {safety_backup['filename']}.",
                flush=True,
            )
            restore_backup(settings, arguments.filename, arguments.confirmation)
            print(f"Restored {arguments.filename} into {settings.app_environment}.")
            return 0
        if arguments.command == "validate":
            result = validate_backup(settings, arguments.filename)
            print(
                f"Valid {result['environment']} backup {result['filename']} "
                f"at schema {result['schema_revision']}."
            )
            return 0

        if len(settings.backup_encryption_key.encode("utf-8")) < 32:
            raise ApiError(
                503,
                "backup_key_not_configured",
                "A backup encryption key of at least 32 bytes must be configured.",
            )

        database = Database(settings)
        ensure_environment_identity(database, settings)
        if arguments.command == "create":
            with database.session() as db:
                result = create_backup(db, settings, kind="manual")
            print(result["filename"])
            return 0

        while True:
            try:
                with database.session() as db:
                    result = create_backup(db, settings, kind="automatic")
                print(f"Created automatic backup {result['filename']}.", flush=True)
            except Exception as error:  # scheduled process must retry after transient failures
                print(f"Automatic backup failed: {error}", file=sys.stderr, flush=True)
            time.sleep(settings.backup_interval_hours * 3600)
    except ApiError as error:
        print(error.message, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
