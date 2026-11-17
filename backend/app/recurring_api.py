from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Response

from app.dependencies import Auth, DatabaseSession, WriterAuth
from app.ledger_services import archive_model, restore_model
from app.models import RecurringDefinition
from app.recurring_schemas import (
    ExpectedOccurrenceRead,
    OccurrenceConfirm,
    RecurringAmountChange,
    RecurringCreate,
    RecurringRead,
    RecurringUpdate,
)
from app.recurring_services import (
    change_amount,
    confirm_occurrence,
    create_definition,
    expected_occurrences,
    get_definition,
    list_definitions,
    reopen_occurrence,
    skip_occurrence,
    update_definition,
)

router = APIRouter(prefix="/recurring", tags=["recurring"])


@router.get("", response_model=list[RecurringRead])
def get_recurring(
    _: Auth, db: DatabaseSession, include_archived: bool = False
) -> list[RecurringDefinition]:
    return list_definitions(db, include_archived)


@router.post("", response_model=RecurringRead, status_code=201)
def post_recurring(
    payload: RecurringCreate, _: WriterAuth, db: DatabaseSession
) -> RecurringDefinition:
    return create_definition(db, payload)


@router.get("/expected", response_model=list[ExpectedOccurrenceRead])
def get_expected(
    auth: Auth, db: DatabaseSession, date_from: date, date_to: date
) -> list[dict[str, object]]:
    today = datetime.now(UTC).astimezone(ZoneInfo(auth.user.settings.timezone)).date()
    return expected_occurrences(db, date_from, date_to, today)


@router.get("/{definition_id}", response_model=RecurringRead)
def get_recurring_item(
    definition_id: int, _: Auth, db: DatabaseSession
) -> RecurringDefinition:
    return get_definition(db, definition_id)


@router.patch("/{definition_id}", response_model=RecurringRead)
def patch_recurring(
    definition_id: int, payload: RecurringUpdate, _: WriterAuth, db: DatabaseSession
) -> RecurringDefinition:
    return update_definition(db, get_definition(db, definition_id), payload)


@router.post("/{definition_id}/amount", response_model=RecurringRead)
def post_recurring_amount(
    definition_id: int, payload: RecurringAmountChange, _: WriterAuth, db: DatabaseSession
) -> RecurringDefinition:
    return change_amount(db, get_definition(db, definition_id), payload)


@router.post("/{definition_id}/archive", response_model=RecurringRead)
def archive_recurring(
    definition_id: int, _: WriterAuth, db: DatabaseSession
) -> RecurringDefinition:
    return archive_model(db, get_definition(db, definition_id))


@router.post("/{definition_id}/restore", response_model=RecurringRead)
def restore_recurring(
    definition_id: int, _: WriterAuth, db: DatabaseSession
) -> RecurringDefinition:
    return restore_model(db, get_definition(db, definition_id))


@router.post(
    "/{definition_id}/occurrences/{due_date}/confirm",
    response_model=ExpectedOccurrenceRead,
)
def post_confirm_occurrence(
    definition_id: int,
    due_date: date,
    payload: OccurrenceConfirm,
    auth: WriterAuth,
    db: DatabaseSession,
) -> dict[str, object]:
    return confirm_occurrence(
        db,
        get_definition(db, definition_id),
        due_date,
        payload,
        auth.user.settings.base_currency,
        actor_user_id=auth.user.user_id,
    )


@router.post(
    "/{definition_id}/occurrences/{due_date}/skip",
    response_model=ExpectedOccurrenceRead,
)
def post_skip_occurrence(
    definition_id: int, due_date: date, auth: WriterAuth, db: DatabaseSession
) -> dict[str, object]:
    return skip_occurrence(
        db, get_definition(db, definition_id), due_date, actor_user_id=auth.user.user_id
    )


@router.post("/{definition_id}/occurrences/{due_date}/reopen", status_code=204)
def post_reopen_occurrence(
    definition_id: int,
    due_date: date,
    response: Response,
    _: WriterAuth,
    db: DatabaseSession,
) -> Response:
    reopen_occurrence(db, get_definition(db, definition_id), due_date)
    response.status_code = 204
    return response
