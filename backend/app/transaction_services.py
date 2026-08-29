from __future__ import annotations

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.errors import ApiError
from app.ledger_schemas import TransactionCreate, TransactionSplitInput, TransactionUpdate
from app.ledger_services import get_model, normalize_name
from app.models import (
    Account,
    Category,
    Provider,
    RefundLink,
    ReimbursementLink,
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
    split_payloads = payload.splits or [
        _legacy_split_payload(
            original_amount,
            payload.category_id,
            payload.tag_ids,
            payload.is_base_cost,
        )
    ]
    model.splits = _build_splits(
        db,
        split_payloads,
        payload.transaction_kind.value,
        converted_amount,
        fx_rate,
    )
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
    is_split = len(model.splits) > 1
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
    amount_fields = {"original_amount", "original_currency", "converted_amount", "fx_rate"}
    if (
        is_split
        and amount_fields.intersection(payload.model_fields_set)
        and payload.splits is None
    ):
        raise ApiError(
            422,
            "split_update_required",
            "Changing a split transaction amount or conversion requires all split amounts.",
        )
    split_classification_fields = {"category_id", "tag_ids", "is_base_cost"}
    if (
        is_split
        and payload.splits is None
        and split_classification_fields.intersection(payload.model_fields_set)
    ):
        raise ApiError(
            422,
            "split_update_required",
            "Changing split classification requires all split classifications.",
        )
    if (
        payload.splits is not None
        and (
            values.get("category_id") is not None
            or bool(values.get("tag_ids"))
            or values.get("is_base_cost") is True
        )
    ):
        raise ApiError(
            422,
            "split_classification_conflict",
            "Split transactions keep categories, tags, and base-cost flags on each split.",
        )
    primary_split = model.splits[0]
    category_id = values.get("category_id", primary_split.category_id)
    amount = values.get("original_amount", model.original_amount).quantize(MONEY_QUANTUM)
    currency = values.get("original_currency", model.original_currency)

    _active_model(db, Account, account_id, "Account")
    if provider_id is not None:
        _active_model(db, Provider, provider_id, "Provider")
    category = (
        _category_for_kind(db, category_id, transaction_kind)
        if payload.splits is None
        else None
    )

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

    if payload.splits is not None:
        split_total = sum(
            (split.original_amount for split in payload.splits), Decimal("0")
        ).quantize(MONEY_QUANTUM)
        if split_total != amount:
            raise ApiError(
                422,
                "split_amount_mismatch",
                "Split amounts must equal the transaction amount.",
                [{"expected": str(amount), "actual": str(split_total)}],
            )
        model.splits = _build_splits(
            db, payload.splits, transaction_kind, converted_amount, fx_rate
        )
    elif not is_split:
        primary_split.category_id = category.category_id if category is not None else None
        primary_split.original_amount = amount
        primary_split.converted_amount = converted_amount
        if "is_base_cost" in values:
            primary_split.is_base_cost = values["is_base_cost"]
        if "tag_ids" in values:
            primary_split.tags = _active_tags(db, values["tag_ids"] or [])

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


def _ledger_filter_expressions(
    *,
    account_id: int | None = None,
    provider_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
    original_currency: str | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    search: str | None = None,
) -> list[Any]:
    filters: list[Any] = [
        Transaction.transaction_kind.in_(("expense", "income", "refund", "reimbursement"))
    ]
    if account_id is not None:
        filters.append(Transaction.account_id == account_id)
    if provider_id is not None:
        filters.append(Transaction.provider_id == provider_id)
    if original_currency is not None:
        filters.append(Transaction.original_currency == original_currency)
    if amount_min is not None:
        filters.append(Transaction.original_amount >= amount_min)
    if amount_max is not None:
        filters.append(Transaction.original_amount <= amount_max)
    if search:
        filters.append(
            Transaction.normalized_description.contains(normalize_name(search), autoescape=True)
        )

    split_conditions = []
    if category_id is not None:
        split_conditions.append(TransactionSplit.category_id == category_id)
    if tag_id is not None:
        split_conditions.append(TransactionSplit.tags.any(Tag.tag_id == tag_id))
    if is_base_cost is not None:
        split_conditions.append(TransactionSplit.is_base_cost.is_(is_base_cost))
    if split_conditions:
        matching_split = and_(*split_conditions)
        matching_recoveries = (
            select(RefundLink.refund_transaction_id)
            .join(
                TransactionSplit,
                TransactionSplit.transaction_id == RefundLink.original_expense_id,
            )
            .where(matching_split)
            .union_all(
                select(ReimbursementLink.reimbursement_transaction_id)
                .join(
                    TransactionSplit,
                    TransactionSplit.transaction_id == ReimbursementLink.original_expense_id,
                )
                .where(matching_split)
            )
        )
        filters.append(
            or_(
                Transaction.splits.any(matching_split),
                Transaction.transaction_id.in_(matching_recoveries),
            )
        )
    return filters


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
    is_base_cost: bool | None,
    original_currency: str | None,
    amount_min: Decimal | None,
    amount_max: Decimal | None,
    search: str | None,
) -> dict[str, Any]:
    filters = _ledger_filter_expressions(
        account_id=account_id,
        provider_id=provider_id,
        category_id=category_id,
        tag_id=tag_id,
        is_base_cost=is_base_cost,
        original_currency=original_currency,
        amount_min=amount_min,
        amount_max=amount_max,
        search=search,
    )
    if not include_archived:
        filters.append(Transaction.status == "active")
    if date_from is not None:
        filters.append(Transaction.transaction_date >= date_from)
    if date_to is not None:
        filters.append(Transaction.transaction_date <= date_to)
    if transaction_kind is not None:
        filters.append(Transaction.transaction_kind == transaction_kind)

    count_statement = select(func.count()).select_from(Transaction).where(*filters)
    statement = (
        select(Transaction)
        .where(*filters)
        .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        .order_by(Transaction.transaction_date.desc(), Transaction.transaction_id.desc())
        .limit(limit)
        .offset(offset)
    )
    models = list(db.scalars(statement))
    recovery_links = _linked_expense_ids(
        db, [model.transaction_id for model in models]
    )
    return {
        "items": [
            transaction_values(
                model, linked_expense_id=recovery_links.get(model.transaction_id)
            )
            for model in models
        ],
        "total": db.scalar(count_statement) or 0,
        "limit": limit,
        "offset": offset,
    }


def ledger_summary(
    db: DbSession,
    date_from: date,
    date_to: date,
    base_currency: str,
    *,
    account_id: int | None = None,
    provider_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
) -> dict[str, Any]:
    in_period = [
        Transaction.status == "active",
        Transaction.transaction_date >= date_from,
        Transaction.transaction_date <= date_to,
        *_ledger_filter_expressions(
            account_id=account_id,
            provider_id=provider_id,
            category_id=category_id,
            tag_id=tag_id,
            is_base_cost=is_base_cost,
        ),
    ]
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
                            Transaction.transaction_kind.in_(
                                ("expense", "refund", "reimbursement")
                            )
                            & usable_conversion[0]
                            & usable_conversion[1],
                            case(
                                (
                                    Transaction.transaction_kind == "expense",
                                    Transaction.converted_amount,
                                ),
                                else_=-Transaction.converted_amount,
                            ),
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
    income_value = Decimal(income).quantize(MONEY_QUANTUM)
    expense_value = Decimal(expenses).quantize(MONEY_QUANTUM)
    if category_id is not None or tag_id is not None or is_base_cost is not None:
        filtered_analysis = _ledger_analysis_period(
            db,
            date_from,
            date_to,
            base_currency,
            account_id=account_id,
            provider_id=provider_id,
            category_id=category_id,
            tag_id=tag_id,
            is_base_cost=is_base_cost,
        )
        income_value = sum(
            (point["income"] for point in filtered_analysis["daily"]), Decimal("0")
        )
        expense_value = sum(
            (point["expenses"] for point in filtered_analysis["daily"]), Decimal("0")
        ).quantize(MONEY_QUANTUM)
        income_value = income_value.quantize(MONEY_QUANTUM)
    return {
        "date_from": date_from,
        "date_to": date_to,
        "base_currency": base_currency,
        "income": income_value,
        "expenses": expense_value,
        "net_cash_flow": (income_value - expense_value).quantize(MONEY_QUANTUM),
        "transaction_count": transaction_count,
        "missing_fx_count": missing_fx_count,
    }


def ledger_analysis(
    db: DbSession,
    date_from: date,
    date_to: date,
    base_currency: str,
    comparison_mode: str = "none",
    *,
    account_id: int | None = None,
    provider_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
) -> dict[str, Any]:
    filter_options = {
        "account_id": account_id,
        "provider_id": provider_id,
        "category_id": category_id,
        "tag_id": tag_id,
        "is_base_cost": is_base_cost,
    }
    result = _ledger_analysis_period(
        db, date_from, date_to, base_currency, **filter_options
    )
    if comparison_mode == "none":
        result["comparison"] = None
        return result
    comparison_from, comparison_to = _comparison_period(
        date_from, date_to, comparison_mode
    )
    comparison = _ledger_analysis_period(
        db, comparison_from, comparison_to, base_currency, **filter_options
    )
    comparison_income = sum(
        (point["income"] for point in comparison["daily"]), Decimal("0")
    ).quantize(MONEY_QUANTUM)
    comparison_expenses = sum(
        (point["expenses"] for point in comparison["daily"]), Decimal("0")
    ).quantize(MONEY_QUANTUM)
    result["comparison"] = {
        "mode": comparison_mode,
        "date_from": comparison_from,
        "date_to": comparison_to,
        "income": comparison_income,
        "expenses": comparison_expenses,
        "net_cash_flow": (comparison_income - comparison_expenses).quantize(MONEY_QUANTUM),
        "daily": comparison["daily"],
        "expense_categories": comparison["expense_categories"],
    }
    return result


def _ledger_analysis_period(
    db: DbSession,
    date_from: date,
    date_to: date,
    base_currency: str,
    *,
    account_id: int | None = None,
    provider_id: int | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
) -> dict[str, Any]:
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.status == "active",
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.base_currency == base_currency,
                Transaction.converted_amount.is_not(None),
                *_ledger_filter_expressions(
                    account_id=account_id,
                    provider_id=provider_id,
                    category_id=category_id,
                    tag_id=tag_id,
                    is_base_cost=is_base_cost,
                ),
            )
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
            .order_by(Transaction.transaction_date)
        )
    )
    links = _linked_expense_ids(db, [model.transaction_id for model in transactions])
    original_ids = set(links.values())
    originals = {
        model.transaction_id: model
        for model in db.scalars(
            select(Transaction)
            .where(Transaction.transaction_id.in_(original_ids))
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        )
    }
    category_ids = {
        split.category_id
        for model in (*transactions, *originals.values())
        for split in model.splits
        if split.category_id is not None
    }
    category_names = {
        category.category_id: category.name
        for category in db.scalars(select(Category).where(Category.category_id.in_(category_ids)))
    }
    daily: dict[date, dict[str, Decimal]] = {}
    categories: dict[int | None, dict[str, Any]] = {}
    for model in transactions:
        assert model.converted_amount is not None
        day = daily.setdefault(
            model.transaction_date,
            {"income": Decimal("0"), "expenses": Decimal("0")},
        )
        if model.transaction_kind == TransactionKind.INCOME:
            income_contributions = _split_category_amounts(
                model,
                category_id=category_id,
                tag_id=tag_id,
                is_base_cost=is_base_cost,
            )
            day["income"] += sum(income_contributions.values(), Decimal("0"))
            continue
        sign = (
            Decimal("1")
            if model.transaction_kind == TransactionKind.EXPENSE
            else Decimal("-1")
        )
        if model.transaction_kind == TransactionKind.EXPENSE:
            contributions = _split_category_amounts(
                model,
                category_id=category_id,
                tag_id=tag_id,
                is_base_cost=is_base_cost,
            )
        else:
            original = originals[links[model.transaction_id]]
            contributions = _allocate_recovery_to_categories(
                original,
                model.converted_amount,
                category_id=category_id,
                tag_id=tag_id,
                is_base_cost=is_base_cost,
            )
        day["expenses"] += sign * sum(contributions.values(), Decimal("0"))
        for contribution_category_id, amount in contributions.items():
            bucket = categories.setdefault(
                contribution_category_id,
                {"amount": Decimal("0"), "transaction_count": 0},
            )
            bucket["amount"] += sign * amount
            bucket["transaction_count"] += 1

    return {
        "date_from": date_from,
        "date_to": date_to,
        "base_currency": base_currency,
        "daily": [
            {
                "date": day_date,
                "income": values["income"].quantize(MONEY_QUANTUM),
                "expenses": values["expenses"].quantize(MONEY_QUANTUM),
                "net_cash_flow": (values["income"] - values["expenses"]).quantize(
                    MONEY_QUANTUM
                ),
            }
            for day_date, values in daily.items()
        ],
        "expense_categories": [
            {
                "category_id": category_id,
                "category_name": category_names.get(category_id),
                "amount": values["amount"].quantize(MONEY_QUANTUM),
                "transaction_count": values["transaction_count"],
            }
            for category_id, values in sorted(
                categories.items(),
                key=lambda item: (-item[1]["amount"], category_names.get(item[0], "")),
            )
        ],
    }


def _comparison_period(
    date_from: date, date_to: date, comparison_mode: str
) -> tuple[date, date]:
    if comparison_mode == "previous_period":
        period_length = date_to - date_from
        comparison_to = date_from - timedelta(days=1)
        return comparison_to - period_length, comparison_to
    if comparison_mode == "previous_year":
        return _shift_year(date_from, -1), _shift_year(date_to, -1)
    raise ApiError(422, "comparison_mode_invalid", "Comparison mode is not supported.")


def _shift_year(value: date, delta: int) -> date:
    try:
        return value.replace(year=value.year + delta)
    except ValueError:
        return value.replace(year=value.year + delta, day=28)


def transaction_values(
    model: Transaction, *, linked_expense_id: int | None = None
) -> dict[str, Any]:
    is_split = len(model.splits) > 1
    split = model.splits[0] if not is_split else None
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
        "category_id": split.category_id if split is not None else None,
        "tag_ids": sorted(tag.tag_id for tag in split.tags) if split is not None else [],
        "is_base_cost": split.is_base_cost if split is not None else False,
        "is_split": is_split,
        "splits": [
            {
                "transaction_split_id": component.transaction_split_id,
                "original_amount": component.original_amount,
                "converted_amount": component.converted_amount,
                "category_id": component.category_id,
                "tag_ids": sorted(tag.tag_id for tag in component.tags),
                "is_base_cost": component.is_base_cost,
                "memo": component.memo,
            }
            for component in model.splits
        ],
        "linked_expense_id": linked_expense_id,
        "status": model.status,
        "archived_at": model.archived_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _linked_expense_ids(db: DbSession, transaction_ids: list[int]) -> dict[int, int]:
    if not transaction_ids:
        return {}
    links = {
        recovery_id: expense_id
        for expense_id, recovery_id in db.execute(
            select(RefundLink.original_expense_id, RefundLink.refund_transaction_id).where(
                RefundLink.refund_transaction_id.in_(transaction_ids)
            )
        )
    }
    links.update(
        {
            recovery_id: expense_id
            for expense_id, recovery_id in db.execute(
                select(
                    ReimbursementLink.original_expense_id,
                    ReimbursementLink.reimbursement_transaction_id,
                ).where(ReimbursementLink.reimbursement_transaction_id.in_(transaction_ids))
            )
        }
    )
    return links


def _split_category_amounts(
    model: Transaction,
    *,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
) -> dict[int | None, Decimal]:
    amounts: dict[int | None, Decimal] = {}
    for split in model.splits:
        if split.converted_amount is None or not _split_matches(
            split,
            category_id=category_id,
            tag_id=tag_id,
            is_base_cost=is_base_cost,
        ):
            continue
        amounts[split.category_id] = (
            amounts.get(split.category_id, Decimal("0")) + split.converted_amount
        )
    return amounts


def _allocate_recovery_to_categories(
    original: Transaction,
    recovery_amount: Decimal,
    *,
    category_id: int | None = None,
    tag_id: int | None = None,
    is_base_cost: bool | None = None,
) -> dict[int | None, Decimal]:
    allocations: dict[int | None, Decimal] = {}
    for split, amount in allocate_recovery_to_splits(original, recovery_amount):
        if not _split_matches(
            split,
            category_id=category_id,
            tag_id=tag_id,
            is_base_cost=is_base_cost,
        ):
            continue
        allocations[split.category_id] = allocations.get(
            split.category_id, Decimal("0")
        ) + amount
    return allocations


def allocate_recovery_to_splits(
    original: Transaction, recovery_amount: Decimal
) -> list[tuple[TransactionSplit, Decimal]]:
    weights = [split.converted_amount for split in original.splits]
    if any(weight is None for weight in weights):
        weights = [split.original_amount for split in original.splits]
    precise_weights = [Decimal(weight) for weight in weights if weight is not None]
    total_weight = sum(precise_weights, Decimal("0"))
    allocations: list[tuple[TransactionSplit, Decimal]] = []
    remaining = recovery_amount
    for index, (split, weight) in enumerate(
        zip(original.splits, precise_weights, strict=True)
    ):
        amount = (
            remaining
            if index == len(original.splits) - 1
            else (recovery_amount * weight / total_weight).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
        )
        remaining -= amount
        allocations.append((split, amount))
    return allocations


def _split_matches(
    split: TransactionSplit,
    *,
    category_id: int | None,
    tag_id: int | None,
    is_base_cost: bool | None,
) -> bool:
    return (
        (category_id is None or split.category_id == category_id)
        and (tag_id is None or any(tag.tag_id == tag_id for tag in split.tags))
        and (is_base_cost is None or split.is_base_cost is is_base_cost)
    )


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


def _legacy_split_payload(
    amount: Decimal,
    category_id: int | None,
    tag_ids: list[int],
    is_base_cost: bool,
) -> TransactionSplitInput:
    return TransactionSplitInput(
        original_amount=amount,
        category_id=category_id,
        tag_ids=tag_ids,
        is_base_cost=is_base_cost,
    )


def _build_splits(
    db: DbSession,
    payloads: list[TransactionSplitInput],
    transaction_kind: str,
    converted_total: Decimal | None,
    fx_rate: Decimal | None,
) -> list[TransactionSplit]:
    original_amounts = [payload.original_amount.quantize(MONEY_QUANTUM) for payload in payloads]
    if converted_total is None:
        converted_amounts: list[Decimal | None] = [None for _ in payloads]
    else:
        assert fx_rate is not None
        converted_amounts = [
            (amount * fx_rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            for amount in original_amounts
        ]
        converted_amounts[-1] += converted_total - sum(converted_amounts, Decimal("0"))
        if any(amount <= 0 for amount in converted_amounts):
            raise ApiError(
                422,
                "split_converted_amount_too_small",
                "Each split must remain positive after conversion and decimal rounding.",
            )

    components: list[TransactionSplit] = []
    for payload, original_amount, converted_amount in zip(
        payloads, original_amounts, converted_amounts, strict=True
    ):
        category = _category_for_kind(db, payload.category_id, transaction_kind)
        components.append(
            TransactionSplit(
                category_id=category.category_id if category is not None else None,
                original_amount=original_amount,
                converted_amount=converted_amount,
                is_base_cost=payload.is_base_cost,
                memo=payload.memo,
                tags=_active_tags(db, payload.tag_ids),
            )
        )
    return components


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
