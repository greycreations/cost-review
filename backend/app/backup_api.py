from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.backup_services import (
    create_backup,
    list_backups,
    resolve_backup_path,
    validate_backup,
)
from app.dependencies import Auth, CsrfAuth, DatabaseSession, RuntimeSettings
from app.schemas import BackupRead, BackupValidationRead

router = APIRouter(prefix="/backups", tags=["backup-and-restore"])


@router.get("", response_model=list[BackupRead])
def get_backups(_: Auth, settings: RuntimeSettings) -> list[dict[str, object]]:
    return list_backups(settings)


@router.post("", response_model=BackupRead, status_code=201)
def post_backup(
    _: CsrfAuth,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> dict[str, object]:
    return create_backup(db, settings, kind="manual")


@router.post("/{filename}/validate", response_model=BackupValidationRead)
def post_validate_backup(
    filename: str,
    _: CsrfAuth,
    settings: RuntimeSettings,
) -> dict[str, object]:
    return validate_backup(settings, filename)


@router.get("/{filename}/download", response_class=FileResponse)
def download_backup(filename: str, _: Auth, settings: RuntimeSettings) -> FileResponse:
    path = resolve_backup_path(settings, filename)
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=path.name,
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )
