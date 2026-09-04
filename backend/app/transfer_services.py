from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.audit_services import record_model_created, record_pending_audits
from app.errors import ApiError
from app.ledger_schemas import TransferCreate, TransferUpdate
from app.ledger_services import get_model, normalize_name
from app.models import Account, Transaction, TransactionSplit, TransferLink
from app.transaction_services import MONEY_QUANTUM, resolve_conversion


def create_transfer(
    db: DbSession, payload: TransferCreate, base_currency: str
) -> TransferLink:
    source_account = _active_account(db, payload.source_account_id)
    destination_account = _active_account(db, payload.destination_account_id)
    source_amount = payload.source_amount.quantize(MONEY_QUANTUM)
    destination_amount = payload.destination_amount.quantize(MONEY_QUANTUM)
    _validate_accounts_and_amounts(
        source_account,
        destination_account,
        source_amount,
        destination_amount,
        payload.purpose.value,
    )

    source_conversion = resolve_conversion(
        source_amount,
        source_account.currency,
        base_currency,
        payload.source_converted_amount,
        payload.source_fx_rate,
    )
    destination_conversion = resolve_conversion(
        destination_amount,
        destination_account.currency,
        base_currency,
        payload.destination_converted_amount,
        payload.destination_fx_rate,
    )
    source_conversion, destination_conversion = _align_conversions(
        source_amount,
        source_account.currency,
        destination_amount,
        destination_account.currency,
        base_currency,
        source_conversion,
        destination_conversion,
    )

    outgoing = _transfer_leg(
        account=source_account,
        transaction_date=payload.transaction_date,
        posting_date=payload.source_posting_date,
        description=payload.description,
        amount=source_amount,
        base_currency=base_currency,
        conversion=source_conversion,
        source_reference=payload.source_reference,
        notes=payload.notes,
    )
    incoming = _transfer_leg(
        account=destination_account,
        transaction_date=payload.transaction_date,
        posting_date=payload.destination_posting_date,
        description=payload.description,
        amount=destination_amount,
        base_currency=base_currency,
        conversion=destination_conversion,
        source_reference=payload.source_reference,
        notes=payload.notes,
    )
    db.add_all([outgoing, incoming])
    db.flush()
    record_model_created(db, outgoing)
    record_model_created(db, incoming)
    link = TransferLink(
        outgoing_transaction_id=outgoing.transaction_id,
        incoming_transaction_id=incoming.transaction_id,
        purpose=payload.purpose.value,
        outgoing_transaction=outgoing,
        incoming_transaction=incoming,
    )
    db.add(link)
    _commit(db)
    return link


def update_transfer(
    db: DbSession,
    link: TransferLink,
    payload: TransferUpdate,
    base_currency: str,
) -> TransferLink:
    outgoing = link.outgoing_transaction
    incoming = link.incoming_transaction
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(
        values,
        {
            "source_account_id",
            "destination_account_id",
            "purpose",
            "transaction_date",
            "source_posting_date",
            "destination_posting_date",
            "description",
            "source_amount",
            "destination_amount",
        },
    )

    source_account = _active_account(
        db, values.get("source_account_id", outgoing.account_id)
    )
    destination_account = _active_account(
        db, values.get("destination_account_id", incoming.account_id)
    )
    source_amount = values.get("source_amount", outgoing.original_amount).quantize(
        MONEY_QUANTUM
    )
    destination_amount = values.get(
        "destination_amount", incoming.original_amount
    ).quantize(MONEY_QUANTUM)
    purpose = values.get("purpose", link.purpose)
    if hasattr(purpose, "value"):
        purpose = purpose.value
    _validate_accounts_and_amounts(
        source_account,
        destination_account,
        source_amount,
        destination_amount,
        purpose,
    )

    source_conversion = _updated_conversion(
        values=values,
        prefix="source",
        previous=outgoing,
        amount=source_amount,
        currency=source_account.currency,
        base_currency=base_currency,
        account_changed=source_account.account_id != outgoing.account_id,
    )
    destination_conversion = _updated_conversion(
        values=values,
        prefix="destination",
        previous=incoming,
        amount=destination_amount,
        currency=destination_account.currency,
        base_currency=base_currency,
        account_changed=destination_account.account_id != incoming.account_id,
    )
    source_conversion, destination_conversion = _align_conversions(
        source_amount,
        source_account.currency,
        destination_amount,
        destination_account.currency,
        base_currency,
        source_conversion,
        destination_conversion,
    )

    transaction_date = values.get("transaction_date", outgoing.transaction_date)
    description = values.get("description", outgoing.description)
    source_reference = values.get("source_reference", outgoing.source_reference)
    notes = values.get("notes", outgoing.notes)
    _apply_leg_values(
        outgoing,
        account=source_account,
        transaction_date=transaction_date,
        posting_date=values.get("source_posting_date", outgoing.posting_date),
        description=description,
        amount=source_amount,
        base_currency=base_currency,
        conversion=source_conversion,
        source_reference=source_reference,
        notes=notes,
    )
    _apply_leg_values(
        incoming,
        account=destination_account,
        transaction_date=transaction_date,
        posting_date=values.get("destination_posting_date", incoming.posting_date),
        description=description,
        amount=destination_amount,
        base_currency=base_currency,
        conversion=destination_conversion,
        source_reference=source_reference,
        notes=notes,
    )
    link.purpose = purpose
    link.updated_at = datetime.now(UTC)
    _commit(db)
    return link


def get_transfer(db: DbSession, transfer_link_id: int) -> TransferLink:
    link = db.scalar(
        select(TransferLink)
        .where(TransferLink.transfer_link_id == transfer_link_id)
        .options(
            selectinload(TransferLink.outgoing_transaction),
            selectinload(TransferLink.incoming_transaction),
        )
    )
    if link is None:
        raise ApiError(404, "not_found", "Transfer was not found.")
    return link


def list_transfers(
    db: DbSession,
    *,
    limit: int,
    offset: int,
    include_archived: bool,
    date_from: date | None,
    date_to: date | None,
    account_id: int | None,
    purpose: str | None,
    search: str | None,
) -> dict[str, Any]:
    outgoing = TransferLink.outgoing_transaction
    incoming = TransferLink.incoming_transaction
    filters = []
    if not include_archived:
        filters.append(outgoing.has(Transaction.status == "active"))
    if date_from is not None:
        filters.append(outgoing.has(Transaction.transaction_date >= date_from))
    if date_to is not None:
        filters.append(outgoing.has(Transaction.transaction_date <= date_to))
    if account_id is not None:
        filters.append(
            or_(
                outgoing.has(Transaction.account_id == account_id),
                incoming.has(Transaction.account_id == account_id),
            )
        )
    if purpose is not None:
        filters.append(TransferLink.purpose == purpose)
    if search:
        filters.append(
            outgoing.has(
                Transaction.normalized_description.contains(
                    normalize_name(search), autoescape=True
                )
            )
        )

    count_statement = select(func.count()).select_from(TransferLink).where(*filters)
    statement = (
        select(TransferLink)
        .join(TransferLink.outgoing_transaction)
        .where(*filters)
        .options(
            selectinload(TransferLink.outgoing_transaction),
            selectinload(TransferLink.incoming_transaction),
        )
        .order_by(
            Transaction.transaction_date.desc(), TransferLink.transfer_link_id.desc()
        )
        .limit(limit)
        .offset(offset)
    )
    return {
        "items": [transfer_values(link) for link in db.scalars(statement)],
        "total": db.scalar(count_statement) or 0,
        "limit": limit,
        "offset": offset,
    }


def set_transfer_archived(
    db: DbSession, link: TransferLink, *, archived: bool
) -> TransferLink:
    outgoing = link.outgoing_transaction
    incoming = link.incoming_transaction
    if not archived:
        _active_account(db, outgoing.account_id)
        _active_account(db, incoming.account_id)
    now = datetime.now(UTC)
    status = "archived" if archived else "active"
    archived_at = now if archived else None
    outgoing.status = status
    incoming.status = status
    outgoing.archived_at = archived_at
    incoming.archived_at = archived_at
    link.updated_at = now
    _commit(db)
    return link


def transfer_values(link: TransferLink) -> dict[str, Any]:
    outgoing = link.outgoing_transaction
    incoming = link.incoming_transaction
    return {
        "transfer_link_id": link.transfer_link_id,
        "source_account_id": outgoing.account_id,
        "destination_account_id": incoming.account_id,
        "purpose": link.purpose,
        "transaction_date": outgoing.transaction_date,
        "source_posting_date": outgoing.posting_date,
        "destination_posting_date": incoming.posting_date,
        "description": outgoing.description,
        "source_amount": outgoing.original_amount,
        "source_currency": outgoing.original_currency,
        "source_converted_amount": outgoing.converted_amount,
        "source_fx_rate": outgoing.fx_rate,
        "source_fx_rate_status": outgoing.fx_rate_status,
        "destination_amount": incoming.original_amount,
        "destination_currency": incoming.original_currency,
        "destination_converted_amount": incoming.converted_amount,
        "destination_fx_rate": incoming.fx_rate,
        "destination_fx_rate_status": incoming.fx_rate_status,
        "base_currency": outgoing.base_currency,
        "source_reference": outgoing.source_reference,
        "notes": outgoing.notes,
        "status": outgoing.status,
        "archived_at": outgoing.archived_at,
        "created_at": link.created_at,
        "updated_at": link.updated_at,
    }


def _transfer_leg(
    *,
    account: Account,
    transaction_date: date,
    posting_date: date,
    description: str,
    amount: Decimal,
    base_currency: str,
    conversion: tuple[Decimal | None, Decimal | None, str],
    source_reference: str | None,
    notes: str | None,
) -> Transaction:
    converted_amount, fx_rate, fx_rate_status = conversion
    return Transaction(
        account_id=account.account_id,
        provider_id=None,
        transaction_kind="transfer",
        transaction_date=transaction_date,
        posting_date=posting_date,
        description=description,
        normalized_description=normalize_name(description),
        original_amount=amount,
        original_currency=account.currency,
        converted_amount=converted_amount,
        base_currency=base_currency,
        fx_rate=fx_rate,
        fx_rate_status=fx_rate_status,
        source_type="manual",
        source_reference=source_reference,
        notes=notes,
        splits=[
            TransactionSplit(
                category_id=None,
                original_amount=amount,
                converted_amount=converted_amount,
                is_base_cost=False,
            )
        ],
    )


def _apply_leg_values(
    model: Transaction,
    *,
    account: Account,
    transaction_date: date,
    posting_date: date,
    description: str,
    amount: Decimal,
    base_currency: str,
    conversion: tuple[Decimal | None, Decimal | None, str],
    source_reference: str | None,
    notes: str | None,
) -> None:
    converted_amount, fx_rate, fx_rate_status = conversion
    model.account_id = account.account_id
    model.transaction_date = transaction_date
    model.posting_date = posting_date
    model.description = description
    model.normalized_description = normalize_name(description)
    model.original_amount = amount
    model.original_currency = account.currency
    model.converted_amount = converted_amount
    model.base_currency = base_currency
    model.fx_rate = fx_rate
    model.fx_rate_status = fx_rate_status
    model.source_reference = source_reference
    model.notes = notes
    split = model.splits[0]
    split.original_amount = amount
    split.converted_amount = converted_amount


def _updated_conversion(
    *,
    values: dict[str, Any],
    prefix: str,
    previous: Transaction,
    amount: Decimal,
    currency: str,
    base_currency: str,
    account_changed: bool,
) -> tuple[Decimal | None, Decimal | None, str]:
    converted_field = f"{prefix}_converted_amount"
    rate_field = f"{prefix}_fx_rate"
    conversion_changed = converted_field in values or rate_field in values
    amount_changed = f"{prefix}_amount" in values
    if conversion_changed:
        return resolve_conversion(
            amount,
            currency,
            base_currency,
            values.get(converted_field),
            values.get(rate_field),
        )
    if account_changed or amount_changed:
        retained_rate = previous.fx_rate if currency == previous.original_currency else None
        return resolve_conversion(
            amount, currency, base_currency, None, retained_rate
        )
    return previous.converted_amount, previous.fx_rate, previous.fx_rate_status


def _align_conversions(
    source_amount: Decimal,
    source_currency: str,
    destination_amount: Decimal,
    destination_currency: str,
    base_currency: str,
    source: tuple[Decimal | None, Decimal | None, str],
    destination: tuple[Decimal | None, Decimal | None, str],
) -> tuple[
    tuple[Decimal | None, Decimal | None, str],
    tuple[Decimal | None, Decimal | None, str],
]:
    source_converted = source[0]
    destination_converted = destination[0]
    if source_converted is not None and destination_converted is None:
        destination = resolve_conversion(
            destination_amount,
            destination_currency,
            base_currency,
            source_converted,
            None,
        )
    elif destination_converted is not None and source_converted is None:
        source = resolve_conversion(
            source_amount,
            source_currency,
            base_currency,
            destination_converted,
            None,
        )
    elif (
        source_converted is not None
        and destination_converted is not None
        and source_converted != destination_converted
    ):
        raise ApiError(
            422,
            "transfer_value_mismatch",
            "Both transfer legs must represent the same value in the base currency. "
            "Record fees as a separate expense.",
        )
    return source, destination


def _validate_accounts_and_amounts(
    source: Account,
    destination: Account,
    source_amount: Decimal,
    destination_amount: Decimal,
    purpose: str,
) -> None:
    if source.account_id == destination.account_id:
        raise ApiError(
            422,
            "transfer_accounts_must_differ",
            "Source and destination accounts must differ.",
        )
    if source.currency == destination.currency and source_amount != destination_amount:
        raise ApiError(
            422,
            "same_currency_transfer_amount_mismatch",
            "A same-currency transfer must have equal source and destination amounts. "
            "Record fees as a separate expense.",
        )
    required_destination_type = {
        "investment": "investment",
        "credit_card_payment": "credit_card",
        "debt_repayment": "loan_debt",
    }.get(purpose)
    if (
        required_destination_type is not None
        and destination.account_type != required_destination_type
    ):
        raise ApiError(
            422,
            "transfer_destination_type_mismatch",
            "The selected transfer purpose does not match the destination account type.",
            [{"required_account_type": required_destination_type}],
        )


def _active_account(db: DbSession, account_id: int) -> Account:
    account = get_model(db, Account, account_id, "Account")
    if account.status != "active":
        raise ApiError(
            409,
            "archived_dependency",
            "Archived accounts cannot be used by an active transfer.",
        )
    return account


def _reject_nulls(values: dict[str, Any], fields: set[str]) -> None:
    invalid = sorted(field for field in fields if field in values and values[field] is None)
    if invalid:
        raise ApiError(
            422,
            "required_field_null",
            "Required fields cannot be null.",
            [{"fields": invalid}],
        )


def _commit(db: DbSession) -> None:
    try:
        record_pending_audits(db)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        raise ApiError(
            409,
            "transfer_integrity_conflict",
            "The transfer conflicts with ledger integrity rules.",
            [{"constraint": constraint_name}] if constraint_name else None,
        ) from error
