"""Recurring definitions and their Expected occurrences.

Expected occurrences are derived from a definition's schedule and amount
versions every time they are read. They are never Ledger transactions, so they
cannot change balances, summaries or budgets. A household member turns one into
an Actual event by confirming it, either by recording a new transaction or by
linking a transaction that already exists (for example one that was imported).
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.ledger_schemas import TransactionCreate
from app.ledger_services import normalize_name
from app.models import (
    Account,
    Category,
    Provider,
    RecurringDefinition,
    RecurringOccurrence,
    RecurringVersion,
    Transaction,
)
from app.recurring_schemas import (
    OccurrenceConfirm,
    RecurringAmountChange,
    RecurringCreate,
    RecurringUpdate,
)
from app.transaction_services import _commit, create_manual_transaction

MAX_RANGE_DAYS = 400
CANDIDATE_WINDOW_DAYS = 5
HUNDRED = Decimal("100")


# Schedule ------------------------------------------------------------------


def add_months(value: date, months: int, anchor_day: int) -> date:
    """Move by whole months, keeping the anchor day or the month's last day."""

    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(anchor_day, calendar.monthrange(year, month)[1]))


def due_dates(definition: RecurringDefinition, date_from: date, date_to: date) -> list[date]:
    end = min(date_to, definition.end_date) if definition.end_date else date_to
    dates: list[date] = []
    if definition.frequency == "weekly":
        step = timedelta(weeks=definition.interval_count)
        current = definition.start_date
        if current < date_from:
            skipped = (date_from - current).days // step.days
            current += step * skipped
        while current <= end:
            if current >= date_from:
                dates.append(current)
            current += step
        return dates

    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[definition.frequency]
    months *= definition.interval_count
    anchor_day = definition.start_date.day
    index = 0
    if definition.start_date < date_from:
        elapsed = (date_from.year - definition.start_date.year) * 12 + (
            date_from.month - definition.start_date.month
        )
        index = max(0, elapsed // months - 1)
    while True:
        current = add_months(definition.start_date, index * months, anchor_day)
        if current > end:
            return dates
        if current >= date_from:
            dates.append(current)
        index += 1


def version_on(definition: RecurringDefinition, due: date) -> RecurringVersion:
    applicable = [version for version in definition.versions if version.effective_from <= due]
    return applicable[-1] if applicable else definition.versions[0]


# Definitions ----------------------------------------------------------------


def list_definitions(db: DbSession, include_archived: bool) -> list[RecurringDefinition]:
    statement = select(RecurringDefinition).order_by(RecurringDefinition.name)
    if not include_archived:
        statement = statement.where(RecurringDefinition.status == "active")
    return list(db.scalars(statement))


def get_definition(db: DbSession, definition_id: int) -> RecurringDefinition:
    definition = db.get(RecurringDefinition, definition_id)
    if definition is None:
        raise ApiError(404, "recurring_not_found", "The recurring item was not found.")
    return definition


def create_definition(db: DbSession, payload: RecurringCreate) -> RecurringDefinition:
    account = _active(db, Account, payload.account_id, "account")
    _check_references(db, payload.provider_id, payload.category_id, payload.transaction_kind)
    if payload.end_date is not None and payload.end_date < payload.start_date:
        raise ApiError(422, "recurring_end_before_start", "The end date is before the start.")
    definition = RecurringDefinition(
        name=payload.name,
        account_id=account.account_id,
        provider_id=payload.provider_id,
        category_id=payload.category_id,
        transaction_kind=payload.transaction_kind,
        currency=payload.currency or account.currency,
        frequency=payload.frequency,
        interval_count=payload.interval_count,
        start_date=payload.start_date,
        end_date=payload.end_date,
        tolerance_percent=payload.tolerance_percent,
        notes=payload.notes,
    )
    definition.versions.append(
        RecurringVersion(
            effective_from=payload.start_date,
            amount=payload.amount,
            amount_type=payload.amount_type,
        )
    )
    db.add(definition)
    _commit(db)
    db.refresh(definition)
    return definition


def update_definition(
    db: DbSession, definition: RecurringDefinition, payload: RecurringUpdate
) -> RecurringDefinition:
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] is None:
        raise ApiError(422, "validation_failed", "A recurring item needs a name.")
    _check_references(
        db,
        values.get("provider_id"),
        values.get("category_id"),
        definition.transaction_kind,
    )
    if values.get("end_date") is not None and values["end_date"] < definition.start_date:
        raise ApiError(422, "recurring_end_before_start", "The end date is before the start.")
    if "tolerance_percent" in values and values["tolerance_percent"] is None:
        values.pop("tolerance_percent")
    for key, value in values.items():
        setattr(definition, key, value)
    _commit(db)
    db.refresh(definition)
    return definition


def change_amount(
    db: DbSession, definition: RecurringDefinition, payload: RecurringAmountChange
) -> RecurringDefinition:
    """Record a new expected amount from a date without rewriting earlier occurrences."""

    if payload.effective_from < definition.start_date:
        raise ApiError(
            422, "recurring_version_before_start", "A new amount cannot apply before the start."
        )
    existing = next(
        (v for v in definition.versions if v.effective_from == payload.effective_from), None
    )
    if existing is not None:
        existing.amount = payload.amount
        existing.amount_type = payload.amount_type
    else:
        definition.versions.append(
            RecurringVersion(
                effective_from=payload.effective_from,
                amount=payload.amount,
                amount_type=payload.amount_type,
            )
        )
    _commit(db)
    db.refresh(definition)
    return definition


# Expected occurrences -----------------------------------------------------------


def expected_occurrences(
    db: DbSession, date_from: date, date_to: date, today: date
) -> list[dict[str, Any]]:
    if date_to < date_from or (date_to - date_from).days > MAX_RANGE_DAYS:
        raise ApiError(
            422, "date_range_invalid", f"Choose a range of at most {MAX_RANGE_DAYS} days."
        )
    definitions = list_definitions(db, include_archived=False)
    decisions = {
        (item.recurring_definition_id, item.due_date): item
        for item in db.scalars(
            select(RecurringOccurrence).where(
                RecurringOccurrence.due_date >= date_from,
                RecurringOccurrence.due_date <= date_to,
            )
        )
    }
    linked = set(
        db.scalars(
            select(RecurringOccurrence.transaction_id).where(
                RecurringOccurrence.transaction_id.is_not(None)
            )
        )
    )
    window = timedelta(days=CANDIDATE_WINDOW_DAYS)
    candidates_by_account: dict[int, list[Transaction]] = {}
    for definition in definitions:
        if definition.account_id not in candidates_by_account:
            candidates_by_account[definition.account_id] = list(
                db.scalars(
                    select(Transaction).where(
                        Transaction.account_id == definition.account_id,
                        Transaction.status == "active",
                        Transaction.transaction_kind.in_(("expense", "income")),
                        Transaction.transaction_date >= date_from - window,
                        Transaction.transaction_date <= date_to + window,
                    )
                )
            )

    results: list[dict[str, Any]] = []
    for definition in definitions:
        for due in due_dates(definition, date_from, date_to):
            version = version_on(definition, due)
            decision = decisions.get((definition.recurring_definition_id, due))
            if decision is not None:
                status = decision.status
            else:
                status = "overdue" if due < today else "expected"
            candidates = (
                _candidates(
                    definition,
                    version,
                    due,
                    candidates_by_account[definition.account_id],
                    linked,
                )
                if decision is None
                else []
            )
            deviation = decision.deviation_percent if decision is not None else None
            results.append(
                {
                    "recurring_definition_id": definition.recurring_definition_id,
                    "name": definition.name,
                    "account_id": definition.account_id,
                    "transaction_kind": definition.transaction_kind,
                    "due_date": due,
                    "expected_amount": version.amount,
                    "amount_type": version.amount_type,
                    "currency": definition.currency,
                    "status": status,
                    "transaction_id": decision.transaction_id if decision is not None else None,
                    "deviation_percent": deviation,
                    "outside_tolerance": deviation is not None
                    and deviation.copy_abs() > definition.tolerance_percent,
                    "candidates": candidates,
                }
            )
    return sorted(results, key=lambda item: (item["due_date"], item["name"]))


def confirm_occurrence(
    db: DbSession,
    definition: RecurringDefinition,
    due: date,
    payload: OccurrenceConfirm,
    base_currency: str,
    *,
    actor_user_id: int | None,
) -> dict[str, Any]:
    _require_due_date(definition, due)
    _require_undecided(db, definition, due)
    version = version_on(definition, due)
    if payload.transaction_id is not None:
        if db.scalar(
            select(RecurringOccurrence.recurring_occurrence_id).where(
                RecurringOccurrence.transaction_id == payload.transaction_id
            )
        ):
            raise ApiError(
                409,
                "occurrence_already_decided",
                "That transaction already confirms another occurrence.",
            )
        if payload.amount is not None or payload.transaction_date is not None:
            raise ApiError(
                422,
                "validation_failed",
                "Link an existing transaction or record a new one, not both.",
            )
        transaction = db.get(Transaction, payload.transaction_id)
        if (
            transaction is None
            or transaction.status != "active"
            or transaction.account_id != definition.account_id
            or transaction.transaction_kind != definition.transaction_kind
        ):
            raise ApiError(
                422,
                "recurring_link_invalid",
                "Link an active transaction of the same kind on the same account.",
            )
        actual = transaction.original_amount
    else:
        if definition.status != "active":
            raise ApiError(409, "recurring_archived", "Restore the recurring item first.")
        actual = payload.amount or version.amount
        transaction = create_manual_transaction(
            db,
            TransactionCreate(
                account_id=definition.account_id,
                provider_id=definition.provider_id,
                transaction_kind=definition.transaction_kind,
                transaction_date=payload.transaction_date or due,
                posting_date=payload.transaction_date or due,
                description=payload.description or definition.name,
                original_amount=actual,
                original_currency=definition.currency,
                category_id=definition.category_id,
                source_reference=f"recurring {definition.recurring_definition_id}:{due}",
            ),
            base_currency,
            source_type="recurring",
            commit=False,
        )
    deviation = ((actual - version.amount) / version.amount * HUNDRED).quantize(
        Decimal("0.0001")
    )
    occurrence = RecurringOccurrence(
        recurring_definition_id=definition.recurring_definition_id,
        due_date=due,
        status="confirmed",
        expected_amount=version.amount,
        deviation_percent=deviation,
        created_by_user_id=actor_user_id,
    )
    occurrence.transaction = transaction
    db.add(occurrence)
    _save_occurrence(db)
    return _occurrence_values(definition, occurrence)


def skip_occurrence(
    db: DbSession, definition: RecurringDefinition, due: date, *, actor_user_id: int | None
) -> dict[str, Any]:
    _require_due_date(definition, due)
    _require_undecided(db, definition, due)
    occurrence = RecurringOccurrence(
        recurring_definition_id=definition.recurring_definition_id,
        due_date=due,
        status="skipped",
        expected_amount=version_on(definition, due).amount,
        created_by_user_id=actor_user_id,
    )
    db.add(occurrence)
    _save_occurrence(db)
    return _occurrence_values(definition, occurrence)


def reopen_occurrence(db: DbSession, definition: RecurringDefinition, due: date) -> None:
    """Remove a skip or a link. A transaction recorded on confirmation is kept."""

    occurrence = db.scalar(
        select(RecurringOccurrence).where(
            RecurringOccurrence.recurring_definition_id == definition.recurring_definition_id,
            RecurringOccurrence.due_date == due,
        )
    )
    if occurrence is None:
        raise ApiError(404, "occurrence_not_found", "That occurrence has no decision.")
    db.delete(occurrence)
    _commit(db)


def _save_occurrence(db: DbSession) -> None:
    try:
        _commit(db)
    except ApiError as error:
        if error.status_code == 409:
            raise ApiError(
                409,
                "occurrence_already_decided",
                "This occurrence or transaction is already linked.",
            ) from error
        raise


def _occurrence_values(
    definition: RecurringDefinition, occurrence: RecurringOccurrence
) -> dict[str, Any]:
    deviation = occurrence.deviation_percent
    return {
        "recurring_definition_id": definition.recurring_definition_id,
        "name": definition.name,
        "account_id": definition.account_id,
        "transaction_kind": definition.transaction_kind,
        "due_date": occurrence.due_date,
        "expected_amount": occurrence.expected_amount,
        "amount_type": version_on(definition, occurrence.due_date).amount_type,
        "currency": definition.currency,
        "status": occurrence.status,
        "transaction_id": occurrence.transaction_id,
        "deviation_percent": deviation,
        "outside_tolerance": deviation is not None
        and deviation.copy_abs() > definition.tolerance_percent,
        "candidates": [],
    }


def _candidates(
    definition: RecurringDefinition,
    version: RecurringVersion,
    due: date,
    transactions: list[Transaction],
    linked: set[int | None],
) -> list[dict[str, Any]]:
    tolerance = max(definition.tolerance_percent, Decimal("0")) / HUNDRED
    lower = version.amount * (1 - tolerance)
    upper = version.amount * (1 + tolerance)
    name = normalize_name(definition.name)
    found = []
    for model in transactions:
        if (
            model.transaction_id in linked
            or model.transaction_kind != definition.transaction_kind
            or model.original_currency != definition.currency
        ):
            continue
        days = abs((model.transaction_date - due).days)
        if days > CANDIDATE_WINDOW_DAYS or not lower <= model.original_amount <= upper:
            continue
        exact = model.original_amount == version.amount
        confidence = 60 + (20 if exact else 0) + max(0, 10 - 2 * days)
        if name and (name in model.normalized_description or model.normalized_description in name):
            confidence += 10
        found.append(
            {
                "transaction_id": model.transaction_id,
                "transaction_date": model.transaction_date,
                "description": model.description,
                "amount": model.original_amount,
                "confidence": min(confidence, 99),
            }
        )
    return sorted(found, key=lambda item: -item["confidence"])[:3]


def _require_undecided(db: DbSession, definition: RecurringDefinition, due: date) -> None:
    if db.scalar(
        select(RecurringOccurrence.recurring_occurrence_id).where(
            RecurringOccurrence.recurring_definition_id == definition.recurring_definition_id,
            RecurringOccurrence.due_date == due,
        )
    ):
        raise ApiError(
            409,
            "occurrence_already_decided",
            "This occurrence is already confirmed or skipped. Reopen it first.",
        )


def _require_due_date(definition: RecurringDefinition, due: date) -> None:
    if due not in due_dates(definition, due, due):
        raise ApiError(
            422, "not_a_due_date", "That date is not a due date of this recurring item."
        )


def _check_references(
    db: DbSession, provider_id: int | None, category_id: int | None, kind: str
) -> None:
    if provider_id is not None:
        _active(db, Provider, provider_id, "provider")
    if category_id is not None:
        category = _active(db, Category, category_id, "category")
        if category.category_kind != kind:
            raise ApiError(
                422,
                "category_kind_mismatch",
                "Income items require an income category and expenses an expense category.",
            )


def _active(db: DbSession, model: Any, identifier: int, name: str) -> Any:
    instance = db.get(model, identifier)
    if instance is None or instance.status != "active":
        raise ApiError(422, f"{name}_not_available", f"Choose an active {name}.")
    return instance
