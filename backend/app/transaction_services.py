from __future__ import annotations

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.errors import ApiError
from app.ledger_schemas import TransactionCreate, TransactionUpdate
from app.ledger_services import get_model, normalize_name
from app.models import (
    Account,
    Category,
    Provider,
    Tag,
    Transaction,
    TransactionKind,
    TransactionSplit,
)

MONEY_QUANTUM = Decimal("0.0001")
RATE_QUANTUM = Decimal("0.0000000001")


def create_manual_transaction(
    db: DbSession, payload: TransactionCreate, base_currency: str
) -> Transaction:
    original_amount = payload.original_amount.quantize(MONEY_QUANTUM)
    account = _active_model(db, Account, payload.account_id, "Account")
    provider = (
        _active_model(db, Provider, payload.provider_id, "Provider")
        if payload.provider_id is not None
        else None
    )
    category = _category_for_kind(db, payload.category_id, payload.transaction_kind.value)
    tags = _active_tags(db, payload.tag_ids)
    converted_amount, fx_rate, fx_rate_status = resolve_conversion(
        original_amount,
        payload.original_currency,
        base_currency,
        payload.converted_amount,
        payload.fx_rate,
    )

    model = Transaction(
        account_id=account.account_id,
        provider_id=provider.provider_id if provider is not None else None,
        transaction_kind=payload.transaction_kind.value,
        transaction_date=payload.transaction_date,
        posting_date=payload.posting_date,
        description=payload.description,
        normalized_description=normalize_name(payload.description),
        original_amount=original_amount,
        original_currency=payload.original_currency,
        converted_amount=converted_amount,
        base_currency=base_currency,
        fx_rate=fx_rate,
        fx_rate_status=fx_rate_status,
        source_type="manual",
        source_reference=payload.source_reference,
        notes=payload.notes,
    )
    model.splits = [
        TransactionSplit(
            category_id=category.category_id if category is not None else None,
            original_amount=original_amount,
            converted_amount=converted_amount,
            is_base_cost=payload.is_base_cost,
            tags=tags,
        )
    ]
    db.add(model)
    _commit(db)
    return model


def update_manual_transaction(
    db: DbSession, model: Transaction, payload: TransactionUpdate
) -> Transaction:
    if model.transaction_kind not in (TransactionKind.EXPENSE, TransactionKind.INCOME):
        raise ApiError(
            409,
            "specialized_transaction_workflow_required",
            "Transfers and other linked events must be edited through their dedicated workflow.",
        )
    if model.source_type != "manual":
        raise ApiError(
            409,
            "source_managed_transaction",
            "Imported or generated transactions must be edited through their source workflow.",
        )
    split = _single_component(model)
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(
        values,
        {
            "account_id",
            "transaction_kind",
            "transaction_date",
            "posting_date",
            "description",
            "original_amount",
            "original_currency",
            "is_base_cost",
        },
    )

    account_id = values.get("account_id", model.account_id)
    provider_id = values.get("provider_id", model.provider_id)
    transaction_kind = values.get("transaction_kind", model.transaction_kind)
    if hasattr(transaction_kind, "value"):
        transaction_kind = transaction_kind.value
    category_id = values.get("category_id", split.category_id)
    amount = values.get("original_amount", model.original_amount).quantize(MONEY_QUANTUM)
    currency = values.get("original_currency", model.original_currency)

    _active_model(db, Account, account_id, "Account")
    if provider_id is not None:
        _active_model(db, Provider, provider_id, "Provider")
    category = _category_for_kind(db, category_id, transaction_kind)

    conversion_changed = bool(
        {"converted_amount", "fx_rate"}.intersection(payload.model_fields_set)
    )
    amount_or_currency_changed = bool(
        {"original_amount", "original_currency"}.intersection(payload.model_fields_set)
    )
    if conversion_changed:
        requested_converted = values.get("converted_amount")
        requested_rate = values.get("fx_rate")
        converted_amount, fx_rate, fx_rate_status = resolve_conversion(
            amount,
            currency,
            model.base_currency,
            requested_converted,
            requested_rate,
        )
    elif amount_or_currency_changed:
        retained_rate = model.fx_rate if currency == model.original_currency else None
        converted_amount, fx_rate, fx_rate_status = resolve_conversion(
            amount,
            currency,
            model.base_currency,
            None,
            retained_rate,
        )
    else:
        converted_amount = model.converted_amount
        fx_rate = model.fx_rate
        fx_rate_status = model.fx_rate_status

    model.account_id = account_id
    model.provider_id = provider_id
    model.transaction_kind = transaction_kind
    model.original_amount = amount
    model.original_currency = currency
    model.converted_amount = converted_amount
    model.fx_rate = fx_rate
    model.fx_rate_status = fx_rate_status
    for field_name in (
        "transaction_date",
        "posting_date",
        "description",
        "source_reference",
        "notes",
    ):
        if field_name in values:
            setattr(model, field_name, values[field_name])
    if "description" in values:
        model.normalized_description = normalize_name(values["description"])

    split.category_id = category.category_id if category is not None else None
    split.original_amount = amount
    split.converted_amount = converted_amount
    if "is_base_cost" in values:
        split.is_base_cost = values["is_base_cost"]
    if "tag_ids" in values:
        split.tags = _active_tags(db, values["tag_ids"] or [])

    _commit(db)
    return model


def get_transaction(db: DbSession, transaction_id: int) -> Transaction:
    model = db.scalar(
        select(Transaction)
        .where(Transaction.transaction_id == transaction_id)
        .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
    )
    if model is None:
        raise ApiError(404, "not_found", "Transaction was not found.")
    return model


def get_manual_transaction(db: DbSession, transaction_id: int) -> Transaction:
    model = get_transaction(db, transaction_id)
    if model.transaction_kind not in (TransactionKind.EXPENSE, TransactionKind.INCOME):
        raise ApiError(
            404,
            "not_found",
            "Transaction was not found in the income and expense workflow.",
        )
    return model


def list_transactions(
    db: DbSession,
    *,
    limit: int,
    offset: int,
    include_archived: bool,
    date_from: date | None,
    date_to: date | None,
    transaction_kind: str | None,
    account_id: int | None,
    provider_id: int | None,
    category_id: int | None,
    tag_id: int | None,
    search: str | None,
) -> dict[str, Any]:
    filters = [Transaction.transaction_kind.in_(("expense", "income"))]
    if not include_archived:
        filters.append(Transaction.status == "active")
    if date_from is not None:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to is not None:
        filters.append(Transaction.transaction_date <= date_to)
    if transaction_kind is not None:
        filters.append(Transaction.transaction_kind == transaction_kind)
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if provider_id is not None:
        filters.append(Transaction.provider_id == provider_id)
    if category_id is not None:
        filters.append(Transaction.splits.any(TransactionSplit.category_id == category_id))
    if tag_id is not None:
        filters.append(Transaction.splits.any(TransactionSplit.tags.any(Tag.tag_id == tag_id)))
    if search:
        filters.append(
            Transaction.normalized_description.contains(normalize_name(search), autoescape=True)
        )

    count_statement = select(func.count()).select_from(Transaction).where(*filters)
    statement = (
        select(Transaction)
        .where(*filters)
        .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        .order_by(Transaction.transaction_date.desc(), Transaction.transaction_id.desc())
        .limit(limit)
        .offset(offset)
    )
    return {
        "items": [transaction_values(model) for model in db.scalars(statement)],
        "total": db.scalar(count_statement) or 0,
        "limit": limit,
        "offset": offset,
    }


def ledger_summary(
    db: DbSession, date_from: date, date_to: date, base_currency: str
) -> dict[str, Any]:
    in_period = (
        Transaction.status == "active",
        Transaction.transaction_kind.in_(("expense", "income")),
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
    )
    usable_conversion = (
        Transaction.base_currency == base_currency,
        Transaction.converted_amount.is_not(None),
    )
    income, expenses, transaction_count, missing_fx_count = db.execute(
        select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_kind == "income")
                            & usable_conversion[0]
                            & usable_conversion[1],
                            Transaction.converted_amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            (Transaction.transaction_kind == "expense")
                            & usable_conversion[0]
                            & usable_conversion[1],
                            Transaction.converted_amount,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.count(Transaction.transaction_id),
            func.coalesce(
                func.sum(
                    case(
                        (
                            or_(
                                Transaction.converted_amount.is_(None),
                                Transaction.base_currency != base_currency,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
        ).where(*in_period)
    ).one()
    income_value = Decimal(income)
    expense_value = Decimal(expenses)
    return {
        "date_from": date_from,
        "date_to": date_to,
        "base_currency": base_currency,
        "income": income_value,
        "expenses": expense_value,
        "net_cash_flow": income_value - expense_value,
        "transaction_count": transaction_count,
        "missing_fx_count": missing_fx_count,
    }


def transaction_values(model: Transaction) -> dict[str, Any]:
    split = _single_component(model)
    return {
        "transaction_id": model.transaction_id,
        "account_id": model.account_id,
        "provider_id": model.provider_id,
        "transaction_kind": model.transaction_kind,
        "transaction_date": model.transaction_date,
        "posting_date": model.posting_date,
        "description": model.description,
        "original_amount": model.original_amount,
        "original_currency": model.original_currency,
        "converted_amount": model.converted_amount,
        "base_currency": model.base_currency,
        "fx_rate": model.fx_rate,
        "fx_rate_status": model.fx_rate_status,
        "source_type": model.source_type,
        "source_reference": model.source_reference,
        "notes": model.notes,
        "category_id": split.category_id,
        "tag_ids": sorted(tag.tag_id for tag in split.tags),
        "is_base_cost": split.is_base_cost,
        "status": model.status,
        "archived_at": model.archived_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def resolve_conversion(
    amount: Decimal,
    original_currency: str,
    base_currency: str,
    converted_amount: Decimal | None,
    fx_rate: Decimal | None,
) -> tuple[Decimal | None, Decimal | None, str]:
    amount = amount.quantize(MONEY_QUANTUM)
    if original_currency == base_currency:
        if converted_amount is not None and converted_amount.quantize(MONEY_QUANTUM) != amount:
            raise ApiError(
                422,
                "same_currency_conversion_mismatch",
                "Converted amount must equal original amount when currencies match.",
            )
        if fx_rate is not None and fx_rate.quantize(RATE_QUANTUM) != Decimal("1").quantize(
            RATE_QUANTUM
        ):
            raise ApiError(
                422,
                "same_currency_rate_mismatch",
                "FX rate must be 1 when currencies match.",
            )
        return amount, Decimal("1").quantize(RATE_QUANTUM), "not_required"

    if converted_amount is None and fx_rate is None:
        return None, None, "missing"
    if fx_rate is None:
        assert converted_amount is not None
        converted_amount = converted_amount.quantize(MONEY_QUANTUM)
        fx_rate = (converted_amount / amount).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
    elif converted_amount is None:
        fx_rate = fx_rate.quantize(RATE_QUANTUM)
        converted_amount = (amount * fx_rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    else:
        fx_rate = fx_rate.quantize(RATE_QUANTUM)
        converted_amount = converted_amount.quantize(MONEY_QUANTUM)
        expected = (amount * fx_rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if converted_amount != expected:
            raise ApiError(
                422,
                "fx_conversion_mismatch",
                "Converted amount does not match original amount multiplied by the FX rate.",
                [{"expected_converted_amount": str(expected)}],
            )
    return converted_amount, fx_rate, "manual"


def _single_component(model: Transaction) -> TransactionSplit:
    if len(model.splits) != 1:
        raise ApiError(
            409,
            "split_transaction_requires_split_editor",
            "This transaction has multiple components and requires the split editor.",
        )
    return model.splits[0]


def _category_for_kind(
    db: DbSession, category_id: int | None, transaction_kind: str
) -> Category | None:
    if category_id is None:
        return None
    category = _active_model(db, Category, category_id, "Category")
    if (
        transaction_kind in (TransactionKind.EXPENSE, TransactionKind.INCOME)
        and category.category_kind != transaction_kind
    ):
        raise ApiError(
            422,
            "category_kind_mismatch",
            "Income transactions require an income category and expenses require "
            "an expense category.",
        )
    return category


def _active_tags(db: DbSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    models = list(db.scalars(select(Tag).where(Tag.tag_id.in_(tag_ids), Tag.status == "active")))
    found = {model.tag_id for model in models}
    missing = sorted(set(tag_ids) - found)
    if missing:
        raise ApiError(
            422,
            "tag_not_available",
            "One or more tags are missing or archived.",
            [{"tag_ids": missing}],
        )
    by_id = {model.tag_id: model for model in models}
    return [by_id[tag_id] for tag_id in tag_ids]


def _active_model[ModelT](
    db: DbSession, model: type[ModelT], model_id: int, resource: str
) -> ModelT:
    instance = get_model(db, model, model_id, resource)
    if instance.status != "active":
        raise ApiError(
            409,
            "archived_dependency",
            f"{resource} is archived and cannot be used by an active transaction.",
        )
    return instance


def _reject_nulls(values: dict[str, Any], required_fields: set[str]) -> None:
    invalid = sorted(
        field for field in required_fields if field in values and values[field] is None
    )
    if invalid:
        raise ApiError(
            422,
            "required_field_null",
            "Required fields cannot be null.",
            [{"fields": invalid}],
        )


def _commit(db: DbSession) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        raise ApiError(
            409,
            "transaction_integrity_conflict",
            "The transaction conflicts with ledger integrity rules.",
            [{"constraint": constraint_name}] if constraint_name else None,
        ) from error
