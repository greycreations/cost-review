from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile
from pydantic import ValidationError

from app.dependencies import Auth, DatabaseSession, WriterAuth
from app.errors import ApiError
from app.import_parsing import MAX_IMPORT_BYTES
from app.import_schemas import (
    ImportBatchRead,
    ImportBulkUpdate,
    ImportPreviewRead,
    ImportProfileRead,
    ImportProfileUpdate,
    ImportRowPage,
    ImportRowRead,
    ImportRowUpdate,
    ImportStageOptions,
    ImportUndoPreviewRead,
    ImportUndoRequest,
)
from app.import_services import (
    batch_values,
    bulk_update_rows,
    commit_batch,
    get_batch,
    get_profile,
    list_batches,
    list_profiles,
    list_rows,
    preview_import,
    set_profile_archived,
    stage_import,
    undo_batch,
    undo_preview,
    update_profile,
    update_row,
)
from app.models import ImportProfile, ImportRow

router = APIRouter(tags=["import"])
ROW_STATUSES = ("ready", "duplicate", "invalid", "skipped", "committed")


async def _read_upload(file: UploadFile) -> tuple[str, bytes]:
    if not file.filename:
        raise ApiError(422, "import_filename_missing", "The uploaded file needs a filename.")
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise ApiError(413, "import_file_too_large", "The import file exceeds 10 MB.")
    return file.filename, content


@router.post("/imports/preview", response_model=ImportPreviewRead)
async def post_import_preview(
    _: WriterAuth,
    db: DatabaseSession,
    file: Annotated[UploadFile, File()],
    delimiter: Annotated[str | None, Form()] = None,
    header_row: Annotated[int, Form(ge=1, le=100)] = 1,
) -> dict[str, object]:
    filename, content = await _read_upload(file)
    return preview_import(db, filename, content, delimiter=delimiter, header_row=header_row)


@router.post("/imports", response_model=ImportBatchRead, status_code=201)
async def post_import(
    auth: WriterAuth,
    db: DatabaseSession,
    file: Annotated[UploadFile, File()],
    options: Annotated[str, Form()],
) -> dict[str, object]:
    filename, content = await _read_upload(file)
    try:
        parsed = ImportStageOptions.model_validate(json.loads(options))
    except (json.JSONDecodeError, ValidationError) as error:
        details = (
            [
                {"location": list(item["loc"]), "message": item["msg"], "type": item["type"]}
                for item in error.errors()
            ]
            if isinstance(error, ValidationError)
            else None
        )
        raise ApiError(
            422, "validation_failed", "The import options are invalid.", details
        ) from error
    batch = stage_import(db, filename, content, parsed, actor_user_id=auth.user.user_id)
    return batch_values(batch)


@router.get("/imports")
def get_imports(
    _: Auth,
    db: DatabaseSession,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    return list_batches(db, limit=limit, offset=offset)


@router.get("/imports/{batch_id}", response_model=ImportBatchRead)
def get_import(batch_id: int, _: Auth, db: DatabaseSession) -> dict[str, object]:
    return batch_values(get_batch(db, batch_id))


@router.get("/imports/{batch_id}/rows", response_model=ImportRowPage)
def get_import_rows(
    batch_id: int,
    _: Auth,
    db: DatabaseSession,
    status: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    if status is not None and status not in ROW_STATUSES:
        raise ApiError(422, "validation_failed", "Unknown import row status.")
    return list_rows(db, get_batch(db, batch_id), status=status, limit=limit, offset=offset)


@router.patch("/imports/{batch_id}/rows/{row_id}", response_model=ImportRowRead)
def patch_import_row(
    batch_id: int,
    row_id: int,
    payload: ImportRowUpdate,
    _: WriterAuth,
    db: DatabaseSession,
) -> ImportRow:
    return update_row(db, get_batch(db, batch_id), row_id, payload)


@router.post("/imports/{batch_id}/rows/bulk")
def post_import_rows_bulk(
    batch_id: int,
    payload: ImportBulkUpdate,
    _: WriterAuth,
    db: DatabaseSession,
) -> dict[str, int]:
    return {"updated": bulk_update_rows(db, get_batch(db, batch_id), payload)}


@router.post("/imports/{batch_id}/commit", response_model=ImportBatchRead)
def post_import_commit(batch_id: int, auth: WriterAuth, db: DatabaseSession) -> dict[str, object]:
    batch = commit_batch(db, get_batch(db, batch_id), auth.user.settings.base_currency)
    return batch_values(batch)


@router.get("/imports/{batch_id}/undo-preview", response_model=ImportUndoPreviewRead)
def get_import_undo_preview(batch_id: int, _: Auth, db: DatabaseSession) -> dict[str, object]:
    return undo_preview(db, get_batch(db, batch_id))


@router.post("/imports/{batch_id}/undo", response_model=ImportBatchRead)
def post_import_undo(
    batch_id: int,
    payload: ImportUndoRequest,
    _: WriterAuth,
    db: DatabaseSession,
) -> dict[str, object]:
    return batch_values(undo_batch(db, get_batch(db, batch_id), payload.confirmation))


@router.get("/import-profiles", response_model=list[ImportProfileRead])
def get_import_profiles(
    _: Auth, db: DatabaseSession, include_archived: bool = False
) -> list[ImportProfile]:
    return list_profiles(db, include_archived)


@router.patch("/import-profiles/{profile_id}", response_model=ImportProfileRead)
def patch_import_profile(
    profile_id: int,
    payload: ImportProfileUpdate,
    _: WriterAuth,
    db: DatabaseSession,
) -> ImportProfile:
    return update_profile(db, get_profile(db, profile_id), payload)


@router.post("/import-profiles/{profile_id}/archive", response_model=ImportProfileRead)
def archive_import_profile(profile_id: int, _: WriterAuth, db: DatabaseSession) -> ImportProfile:
    return set_profile_archived(db, get_profile(db, profile_id), archived=True)


@router.post("/import-profiles/{profile_id}/restore", response_model=ImportProfileRead)
def restore_import_profile(profile_id: int, _: WriterAuth, db: DatabaseSession) -> ImportProfile:
    return set_profile_archived(db, get_profile(db, profile_id), archived=False)
