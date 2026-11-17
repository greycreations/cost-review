"""Stage, review, commit and undo CSV/XLSX imports.

Nothing reaches the Ledger while a batch is staged. Rows are interpreted,
validated and compared with existing history; duplicates and invalid rows stay
visible until the user decides. Committing creates ordinary income and expense
transactions with ``source_type = 'import'`` in one database transaction, and
undoing archives exactly the transactions a batch created.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.audit_services import record_audit
from app.errors import ApiError
from app.import_parsing import (
    ColumnMapping,
    ParsedTable,
    guess_date_format,
    guess_decimal_separator,
    header_signature,
    interpret_row,
    json_safe,
    read_table,
    signature_confidence,
    suggest_mapping,
)
from app.import_schemas import (
    ImportBulkUpdate,
    ImportMappingInput,
    ImportProfileUpdate,
    ImportRowUpdate,
    ImportStageOptions,
)
from app.ledger_schemas import TransactionCreate
from app.ledger_services import normalize_name
from app.models import (
    Account,
    Category,
    ImportBatch,
    ImportProfile,
    ImportRow,
    ImportRowStatus,
    Provider,
    ProviderAlias,
    RefundLink,
    ReimbursementLink,
    Transaction,
)
from app.transaction_services import _commit, create_manual_transaction

DUPLICATE_WINDOW_DAYS = 3
DUPLICATE_THRESHOLD = 60
PREVIEW_ROWS = 20
UNDO_CONFIRMATION = "UNDO IMPORT"


def preview_import(
    db: DbSession,
    filename: str,
    content: bytes,
    *,
    delimiter: str | None = None,
    header_row: int = 1,
) -> dict[str, Any]:
    table = read_table(filename, content, delimiter=delimiter, header_row=header_row)
    mapping: dict[str, Any] = suggest_mapping(table.headers)
    date_values = [row.get(mapping["date_column"]) for row in table.rows] if mapping[
        "date_column"
    ] else []
    amount_columns = [
        mapping[key] for key in ("amount_column", "debit_column", "credit_column") if mapping[key]
    ]
    amount_values = [row.get(column) for row in table.rows for column in amount_columns]
    mapping.update(
        {
            "date_format": guess_date_format(date_values),
            "decimal_separator": guess_decimal_separator(amount_values),
            "amount_sign": "as_is",
            "delimiter": table.delimiter,
            "header_row": header_row,
        }
    )
    signature = header_signature(table.headers)
    suggestions = sorted(
        (
            {
                "import_profile_id": profile.import_profile_id,
                "name": profile.name,
                "confidence": signature_confidence(signature, profile.header_signature),
            }
            for profile in db.scalars(
                select(ImportProfile).where(ImportProfile.status == "active")
            )
        ),
        key=lambda item: (-item["confidence"], item["name"]),
    )
    digest = hashlib.sha256(content).hexdigest()
    previous = [
        {
            "import_batch_id": batch.import_batch_id,
            "status": batch.status,
            "created_at": batch.created_at,
        }
        for batch in db.scalars(
            select(ImportBatch)
            .where(ImportBatch.file_sha256 == digest)
            .order_by(ImportBatch.created_at.desc())
        )
    ]
    return {
        "filename": filename,
        "headers": table.headers,
        "sample_rows": [
            {key: json_safe(value) for key, value in row.items()}
            for row in table.rows[:PREVIEW_ROWS]
        ],
        "row_count": len(table.rows),
        "delimiter": table.delimiter,
        "suggested_mapping": mapping,
        "profile_suggestions": [item for item in suggestions if item["confidence"] > 0],
        "previous_imports": previous,
    }


def stage_import(
    db: DbSession,
    filename: str,
    content: bytes,
    options: ImportStageOptions,
    *,
    actor_user_id: int | None,
) -> ImportBatch:
    account = db.get(Account, options.account_id)
    if account is None or account.status != "active":
        raise ApiError(422, "account_not_available", "Choose an active account for the import.")

    profile: ImportProfile | None = None
    if options.import_profile_id is not None:
        profile = db.get(ImportProfile, options.import_profile_id)
        if profile is None or profile.status != "active":
            raise ApiError(404, "import_profile_not_found", "The import profile was not found.")
    mapping_input = options.mapping or _profile_mapping(profile)  # type: ignore[arg-type]
    table = read_table(
        filename,
        content,
        delimiter=mapping_input.delimiter,
        header_row=mapping_input.header_row,
    )
    _require_columns(table, mapping_input)
    mapping = _column_mapping(mapping_input)

    if options.save_profile_name:
        profile = _save_profile(db, options.save_profile_name, mapping_input, table, account)

    batch = ImportBatch(
        import_profile_id=profile.import_profile_id if profile is not None else None,
        account_id=account.account_id,
        filename=filename[:255],
        file_sha256=hashlib.sha256(content).hexdigest(),
        status="staged",
        row_count=len(table.rows),
        mapping=mapping_input.model_dump(mode="json"),
        created_by_user_id=actor_user_id,
    )
    occurrences: dict[str, int] = defaultdict(int)
    provider_lookup = _provider_lookup(db)
    for index, raw in enumerate(table.rows, start=1):
        interpreted = interpret_row(raw, mapping)
        currency = interpreted.currency or account.currency
        core = _fingerprint_core(account.account_id, interpreted, currency)
        occurrences[core] += 1
        row = ImportRow(
            row_number=index,
            raw={key: json_safe(value) for key, value in raw.items()},
            transaction_date=interpreted.transaction_date,
            posting_date=interpreted.posting_date,
            description=interpreted.description,
            amount=interpreted.amount,
            currency=currency,
            reference=interpreted.reference,
            provider_id=provider_lookup.get(normalize_name(interpreted.description or "")),
            errors=list(interpreted.errors),
            status=ImportRowStatus.INVALID if interpreted.errors else ImportRowStatus.READY,
            fingerprint=_fingerprint(core, occurrences[core]),
        )
        batch.rows.append(row)

    _flag_duplicates(db, account.account_id, batch.rows)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def get_batch(db: DbSession, batch_id: int) -> ImportBatch:
    batch = db.get(ImportBatch, batch_id)
    if batch is None:
        raise ApiError(404, "import_batch_not_found", "The import was not found.")
    return batch


def list_batches(db: DbSession, *, limit: int, offset: int) -> dict[str, Any]:
    total = db.scalar(select(func.count()).select_from(ImportBatch)) or 0
    batches = list(
        db.scalars(
            select(ImportBatch)
            .order_by(ImportBatch.created_at.desc(), ImportBatch.import_batch_id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    counts = _status_counts(db, [batch.import_batch_id for batch in batches])
    return {
        "items": [batch_values(batch, counts.get(batch.import_batch_id, {})) for batch in batches],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def batch_values(batch: ImportBatch, counts: dict[str, int] | None = None) -> dict[str, Any]:
    if counts is None:
        counts = defaultdict(int)
        for row in batch.rows:
            counts[row.status] += 1
    return {
        "import_batch_id": batch.import_batch_id,
        "import_profile_id": batch.import_profile_id,
        "account_id": batch.account_id,
        "filename": batch.filename,
        "status": batch.status,
        "row_count": batch.row_count,
        "status_counts": {status.value: counts.get(status.value, 0) for status in ImportRowStatus},
        "created_by_user_id": batch.created_by_user_id,
        "created_at": batch.created_at,
        "committed_at": batch.committed_at,
        "undone_at": batch.undone_at,
    }


def list_rows(
    db: DbSession,
    batch: ImportBatch,
    *,
    status: str | None,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    filters = [ImportRow.import_batch_id == batch.import_batch_id]
    if status is not None:
        filters.append(ImportRow.status == status)
    total = db.scalar(select(func.count()).select_from(ImportRow).where(*filters)) or 0
    rows = list(
        db.scalars(
            select(ImportRow)
            .where(*filters)
            .order_by(ImportRow.row_number)
            .limit(limit)
            .offset(offset)
        )
    )
    return {"items": rows, "total": total, "limit": limit, "offset": offset}


def update_row(
    db: DbSession, batch: ImportBatch, row_id: int, payload: ImportRowUpdate
) -> ImportRow:
    _require_staged(batch)
    row = db.get(ImportRow, row_id)
    if row is None or row.import_batch_id != batch.import_batch_id:
        raise ApiError(404, "import_row_not_found", "The import row was not found.")
    values = payload.model_dump(exclude_unset=True)
    _apply_row_values(db, row, values)
    db.commit()
    db.refresh(row)
    return row


def bulk_update_rows(db: DbSession, batch: ImportBatch, payload: ImportBulkUpdate) -> int:
    _require_staged(batch)
    rows = list(
        db.scalars(
            select(ImportRow).where(
                ImportRow.import_batch_id == batch.import_batch_id,
                ImportRow.import_row_id.in_(payload.import_row_ids),
            )
        )
    )
    if len(rows) != len(set(payload.import_row_ids)):
        raise ApiError(404, "import_row_not_found", "One or more import rows were not found.")
    values = payload.model_dump(exclude_unset=True, exclude={"import_row_ids"})
    for row in rows:
        _apply_row_values(db, row, values)
    db.commit()
    return len(rows)


def commit_batch(db: DbSession, batch: ImportBatch, base_currency: str) -> ImportBatch:
    db.refresh(batch, with_for_update=True)
    _require_staged(batch)
    ready = [row for row in batch.rows if row.status == ImportRowStatus.READY]
    if not ready:
        raise ApiError(
            422,
            "import_nothing_ready",
            "No rows are approved. Approve at least one row before importing.",
        )
    for row in ready:
        try:
            payload = _transaction_payload(batch, row)
            model = create_manual_transaction(
                db, payload, base_currency, source_type="import", commit=False
            )
        except ApiError as error:
            db.rollback()
            raise ApiError(
                error.status_code,
                error.code,
                f"Row {row.row_number}: {error.message}",
                [{"row_number": row.row_number}],
            ) from error
        row.transaction = model
        row.status = ImportRowStatus.COMMITTED
    batch.status = "committed"
    batch.committed_at = datetime.now(UTC)
    record_audit(
        db,
        entity_type="import_batch",
        entity_id=batch.import_batch_id,
        action="imported",
        changes={
            "filename": batch.filename,
            "account_id": batch.account_id,
            "transaction_count": len(ready),
        },
        source="import",
    )
    _commit(db)
    db.refresh(batch)
    return batch


def undo_preview(db: DbSession, batch: ImportBatch) -> dict[str, Any]:
    transactions = _batch_transactions(batch)
    active = [model for model in transactions if model.status == "active"]
    edited = 0
    if batch.committed_at is not None:
        edited = sum(
            1
            for model in active
            if model.updated_at > batch.committed_at + timedelta(seconds=2)
        )
    linked = _linked_recovery_count(db, [model.transaction_id for model in active])
    expenses = sum(
        (model.original_amount for model in active if model.transaction_kind == "expense"),
        Decimal("0"),
    )
    income = sum(
        (model.original_amount for model in active if model.transaction_kind == "income"),
        Decimal("0"),
    )
    return {
        "import_batch_id": batch.import_batch_id,
        "transaction_count": len(transactions),
        "active_transaction_count": len(active),
        "expenses": expenses.quantize(Decimal("0.0001")),
        "income": income.quantize(Decimal("0.0001")),
        "edited_after_import_count": edited,
        "linked_recovery_count": linked,
        "can_undo": batch.status == "committed" and linked == 0,
    }


def undo_batch(db: DbSession, batch: ImportBatch, confirmation: str) -> ImportBatch:
    if confirmation != UNDO_CONFIRMATION:
        raise ApiError(
            422, "confirmation_mismatch", f"Type {UNDO_CONFIRMATION} exactly to undo the import."
        )
    db.refresh(batch, with_for_update=True)
    if batch.status != "committed":
        raise ApiError(409, "import_not_committed", "Only a committed import can be undone.")
    preview = undo_preview(db, batch)
    if preview["linked_recovery_count"]:
        raise ApiError(
            409,
            "import_has_linked_recoveries",
            "Refunds or reimbursements are linked to imported expenses. "
            "Archive them first.",
            [{"linked_recovery_count": preview["linked_recovery_count"]}],
        )
    now = datetime.now(UTC)
    for model in _batch_transactions(batch):
        if model.status == "active":
            model.status = "archived"
            model.archived_at = now
    batch.status = "undone"
    batch.undone_at = now
    record_audit(
        db,
        entity_type="import_batch",
        entity_id=batch.import_batch_id,
        action="import_undone",
        changes={
            "filename": batch.filename,
            "archived_transaction_count": preview["active_transaction_count"],
        },
        source="import",
    )
    _commit(db)
    db.refresh(batch)
    return batch


def list_profiles(db: DbSession, include_archived: bool) -> list[ImportProfile]:
    statement = select(ImportProfile).order_by(ImportProfile.name)
    if not include_archived:
        statement = statement.where(ImportProfile.status == "active")
    return list(db.scalars(statement))


def get_profile(db: DbSession, profile_id: int) -> ImportProfile:
    profile = db.get(ImportProfile, profile_id)
    if profile is None:
        raise ApiError(404, "import_profile_not_found", "The import profile was not found.")
    return profile


def update_profile(
    db: DbSession, profile: ImportProfile, payload: ImportProfileUpdate
) -> ImportProfile:
    values = payload.model_dump(exclude_unset=True)
    if "name" in values:
        if values["name"] is None:
            raise ApiError(422, "validation_failed", "A profile needs a name.")
        profile.name = values["name"]
        profile.normalized_name = normalize_name(values["name"])
    if "default_account_id" in values:
        profile.default_account_id = values["default_account_id"]
    db.commit()
    db.refresh(profile)
    return profile


def set_profile_archived(db: DbSession, profile: ImportProfile, archived: bool) -> ImportProfile:
    profile.status = "archived" if archived else "active"
    profile.archived_at = datetime.now(UTC) if archived else None
    db.commit()
    db.refresh(profile)
    return profile


def _profile_mapping(profile: ImportProfile) -> ImportMappingInput:
    return ImportMappingInput(
        date_column=profile.date_column,
        description_column=profile.description_column,
        amount_column=profile.amount_column,
        debit_column=profile.debit_column,
        credit_column=profile.credit_column,
        posting_date_column=profile.posting_date_column,
        currency_column=profile.currency_column,
        reference_column=profile.reference_column,
        date_format=profile.date_format,
        decimal_separator=profile.decimal_separator,  # type: ignore[arg-type]
        amount_sign=profile.amount_sign,  # type: ignore[arg-type]
        delimiter=profile.delimiter,
        header_row=profile.header_row,
    )


def _column_mapping(mapping: ImportMappingInput) -> ColumnMapping:
    return ColumnMapping(
        date_column=mapping.date_column,
        description_column=mapping.description_column,
        amount_column=mapping.amount_column,
        debit_column=mapping.debit_column,
        credit_column=mapping.credit_column,
        posting_date_column=mapping.posting_date_column,
        currency_column=mapping.currency_column,
        reference_column=mapping.reference_column,
        date_format=mapping.date_format,
        decimal_separator=mapping.decimal_separator,
        amount_sign=mapping.amount_sign,
    )


def _require_columns(table: ParsedTable, mapping: ImportMappingInput) -> None:
    mapped = [
        value
        for key, value in mapping.model_dump().items()
        if key.endswith("_column") and value is not None
    ]
    missing = [column for column in mapped if column not in table.headers]
    if missing:
        raise ApiError(
            422,
            "import_column_missing",
            "The file does not contain every mapped column.",
            [{"missing_columns": missing, "available_columns": table.headers}],
        )


def _save_profile(
    db: DbSession,
    name: str,
    mapping: ImportMappingInput,
    table: ParsedTable,
    account: Account,
) -> ImportProfile:
    values = mapping.model_dump()
    values["delimiter"] = mapping.delimiter or table.delimiter
    profile = ImportProfile(
        name=name,
        normalized_name=normalize_name(name),
        header_signature=header_signature(table.headers),
        default_account_id=account.account_id,
        **values,
    )
    db.add(profile)
    db.flush()
    return profile


def _fingerprint_core(account_id: int, row: Any, currency: str) -> str:
    return "|".join(
        [
            str(account_id),
            row.transaction_date.isoformat() if row.transaction_date else "",
            str(row.amount) if row.amount is not None else "",
            currency,
            normalize_name(row.description or ""),
        ]
    )


def _fingerprint(core: str, occurrence: int) -> str:
    """Identify a source row so re-importing the same export is recognised.

    Identical rows in one file (two equal purchases on one day) are told
    apart by their occurrence order, so they are not flagged against each other.
    """

    return hashlib.sha256(f"{core}|{occurrence}".encode()).hexdigest()


def _provider_lookup(db: DbSession) -> dict[str, int]:
    lookup = {
        provider.normalized_name: provider.provider_id
        for provider in db.scalars(select(Provider).where(Provider.status == "active"))
    }
    for alias in db.scalars(select(ProviderAlias)):
        lookup.setdefault(alias.normalized_alias, alias.provider_id)
    return lookup


def _flag_duplicates(db: DbSession, account_id: int, rows: list[ImportRow]) -> None:
    candidates = [row for row in rows if row.status == ImportRowStatus.READY]
    if not candidates:
        return

    previous = set(
        db.scalars(
            select(ImportRow.fingerprint)
            .join(ImportBatch, ImportBatch.import_batch_id == ImportRow.import_batch_id)
            .join(Transaction, Transaction.transaction_id == ImportRow.transaction_id)
            .where(
                ImportRow.fingerprint.in_([row.fingerprint for row in candidates]),
                ImportRow.status == ImportRowStatus.COMMITTED,
                ImportBatch.status == "committed",
                Transaction.status == "active",
            )
        )
    )
    previous_transactions = dict(
        db.execute(
            select(ImportRow.fingerprint, ImportRow.transaction_id)
            .join(ImportBatch, ImportBatch.import_batch_id == ImportRow.import_batch_id)
            .where(
                ImportRow.fingerprint.in_(previous),
                ImportRow.status == ImportRowStatus.COMMITTED,
                ImportBatch.status == "committed",
            )
        ).all()
    ) if previous else {}

    dates = [row.transaction_date for row in candidates if row.transaction_date is not None]
    window = timedelta(days=DUPLICATE_WINDOW_DAYS)
    existing: dict[tuple[str, Decimal, str], list[Transaction]] = defaultdict(list)
    for model in db.scalars(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.status == "active",
            Transaction.transaction_kind.in_(("expense", "income")),
            Transaction.transaction_date >= min(dates) - window,
            Transaction.transaction_date <= max(dates) + window,
        )
    ):
        existing[
            (model.transaction_kind, model.original_amount, model.original_currency)
        ].append(model)

    claimed: set[int] = set(previous_transactions.values())
    for row in candidates:
        if row.fingerprint in previous:
            row.status = ImportRowStatus.DUPLICATE
            row.duplicate_confidence = 100
            row.duplicate_reason = "previously_imported"
            row.duplicate_transaction_id = previous_transactions.get(row.fingerprint)
            continue
        if row.amount is None or row.transaction_date is None:
            continue
        kind = "expense" if row.amount < 0 else "income"
        best: tuple[int, Transaction] | None = None
        for model in existing.get((kind, row.amount.copy_abs(), row.currency or ""), []):
            if model.transaction_id in claimed:
                continue
            confidence = _duplicate_confidence(row, model)
            if confidence >= DUPLICATE_THRESHOLD and (best is None or confidence > best[0]):
                best = (confidence, model)
        if best is not None:
            claimed.add(best[1].transaction_id)
            row.status = ImportRowStatus.DUPLICATE
            row.duplicate_confidence = best[0]
            row.duplicate_reason = "matching_transaction"
            row.duplicate_transaction_id = best[1].transaction_id


def _duplicate_confidence(row: ImportRow, model: Transaction) -> int:
    days = abs((model.transaction_date - row.transaction_date).days)  # type: ignore[operator]
    same_text = normalize_name(row.description or "") == model.normalized_description
    if days == 0:
        return 95 if same_text else 80
    return max(0, (85 if same_text else 70) - 5 * days)


def _apply_row_values(db: DbSession, row: ImportRow, values: dict[str, Any]) -> None:
    if row.status == ImportRowStatus.COMMITTED:
        raise ApiError(409, "import_row_committed", "A committed row cannot be changed.")
    requested_status = values.pop("status", None)
    if "category_id" in values and values["category_id"] is not None:
        category = db.get(Category, values["category_id"])
        if category is None or category.status != "active":
            raise ApiError(422, "category_not_available", "Choose an active category.")
    if "provider_id" in values and values["provider_id"] is not None:
        provider = db.get(Provider, values["provider_id"])
        if provider is None or provider.status != "active":
            raise ApiError(422, "provider_not_available", "Choose an active provider.")
    corrected = {"transaction_date", "posting_date", "description", "amount"} & set(values)
    for key, value in values.items():
        setattr(row, key, value)
    if corrected:
        row.errors = _row_errors(row)
        if row.errors:
            row.status = ImportRowStatus.INVALID
        elif row.status == ImportRowStatus.INVALID:
            row.status = ImportRowStatus.READY

    if requested_status == ImportRowStatus.SKIPPED:
        row.status = ImportRowStatus.SKIPPED
    elif requested_status == ImportRowStatus.READY:
        errors = _row_errors(row)
        if errors:
            row.errors = errors
            row.status = ImportRowStatus.INVALID
            raise ApiError(
                422,
                "import_row_invalid",
                f"Row {row.row_number} must be corrected before it can be approved.",
                [{"row_number": row.row_number, "errors": errors}],
            )
        # Approving a duplicate is an explicit decision; its evidence is kept.
        row.status = ImportRowStatus.READY


def _row_errors(row: ImportRow) -> list[str]:
    errors = []
    if row.transaction_date is None:
        errors.append("date_invalid")
    if not row.description:
        errors.append("description_missing")
    if row.amount is None:
        errors.append("amount_invalid")
    elif row.amount == 0:
        errors.append("amount_zero")
    return errors


def _transaction_payload(batch: ImportBatch, row: ImportRow) -> TransactionCreate:
    assert row.amount is not None and row.transaction_date is not None
    try:
        return TransactionCreate(
            account_id=batch.account_id,
            provider_id=row.provider_id,
            transaction_kind="expense" if row.amount < 0 else "income",
            transaction_date=row.transaction_date,
            posting_date=row.posting_date or row.transaction_date,
            description=row.description or "",
            original_amount=row.amount.copy_abs(),
            original_currency=row.currency or "SEK",
            category_id=row.category_id,
            source_reference=(row.reference or f"import {batch.import_batch_id}:{row.row_number}")[
                :240
            ],
        )
    except ValidationError as error:
        raise ApiError(
            422,
            "import_row_invalid",
            "The row cannot become a transaction.",
            [{"row_number": row.row_number, "errors": [str(error)]}],
        ) from error


def _require_staged(batch: ImportBatch) -> None:
    if batch.status != "staged":
        raise ApiError(
            409, "import_not_staged", "This import has already been committed or undone."
        )


def _batch_transactions(batch: ImportBatch) -> list[Transaction]:
    return [row.transaction for row in batch.rows if row.transaction is not None]


def _linked_recovery_count(db: DbSession, transaction_ids: list[int]) -> int:
    if not transaction_ids:
        return 0
    refunds = (
        db.scalar(
            select(func.count())
            .select_from(RefundLink)
            .join(Transaction, Transaction.transaction_id == RefundLink.refund_transaction_id)
            .where(
                RefundLink.original_expense_id.in_(transaction_ids),
                Transaction.status == "active",
            )
        )
        or 0
    )
    reimbursements = (
        db.scalar(
            select(func.count())
            .select_from(ReimbursementLink)
            .join(
                Transaction,
                Transaction.transaction_id == ReimbursementLink.reimbursement_transaction_id,
            )
            .where(
                ReimbursementLink.original_expense_id.in_(transaction_ids),
                Transaction.status == "active",
            )
        )
        or 0
    )
    return refunds + reimbursements


def _status_counts(db: DbSession, batch_ids: list[int]) -> dict[int, dict[str, int]]:
    counts: dict[int, dict[str, int]] = defaultdict(dict)
    if not batch_ids:
        return counts
    for batch_id, status, count in db.execute(
        select(ImportRow.import_batch_id, ImportRow.status, func.count())
        .where(ImportRow.import_batch_id.in_(batch_ids))
        .group_by(ImportRow.import_batch_id, ImportRow.status)
    ):
        counts[batch_id][status] = count
    return counts


__all__ = [
    "UNDO_CONFIRMATION",
    "batch_values",
    "bulk_update_rows",
    "commit_batch",
    "get_batch",
    "get_profile",
    "list_batches",
    "list_profiles",
    "list_rows",
    "preview_import",
    "set_profile_archived",
    "stage_import",
    "undo_batch",
    "undo_preview",
    "update_profile",
    "update_row",
]

