from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import selectinload

from app.budget_schemas import AnalysisGroupCreate, AnalysisGroupUpdate, BudgetCreate, BudgetUpdate
from app.errors import ApiError
from app.ledger_services import normalize_name
from app.models import (
    AnalysisGroup,
    AnalysisGroupCategory,
    AnalysisGroupTag,
    Budget,
    BudgetCategory,
    BudgetTag,
    Category,
    Tag,
    Transaction,
    TransactionSplit,
)
from app.transaction_services import (
    MONEY_QUANTUM,
    _linked_expense_ids,
    allocate_recovery_to_splits,
)


@dataclass(frozen=True)
class CompiledSelection:
    include_categories: frozenset[int]
    exclude_categories: frozenset[int]
    include_tags: frozenset[int]
    exclude_tags: frozenset[int]


def list_analysis_groups(db: DbSession, include_archived: bool = False) -> list[dict[str, Any]]:
    statement = _group_statement()
    if not include_archived:
        statement = statement.where(AnalysisGroup.status == "active")
    return [analysis_group_values(model) for model in db.scalars(statement)]


def get_analysis_group(db: DbSession, group_id: int) -> AnalysisGroup:
    model = db.scalar(_group_statement().where(AnalysisGroup.analysis_group_id == group_id))
    if model is None:
        raise ApiError(404, "not_found", "Analysis Group was not found.")
    return model


def create_analysis_group(db: DbSession, payload: AnalysisGroupCreate) -> AnalysisGroup:
    model = AnalysisGroup(
        name=payload.name, normalized_name=normalize_name(payload.name), notes=payload.notes
    )
    _apply_group_selection(db, model, payload)
    db.add(model)
    _commit(db, "analysis_group_name_exists")
    return get_analysis_group(db, model.analysis_group_id)


def update_analysis_group(
    db: DbSession, model: AnalysisGroup, payload: AnalysisGroupUpdate
) -> AnalysisGroup:
    model.name = payload.name
    model.normalized_name = normalize_name(payload.name)
    model.notes = payload.notes
    _apply_group_selection(db, model, payload)
    _commit(db, "analysis_group_name_exists")
    return get_analysis_group(db, model.analysis_group_id)


def set_analysis_group_archived(
    db: DbSession, model: AnalysisGroup, archived: bool
) -> AnalysisGroup:
    from datetime import UTC, datetime

    if archived:
        active_budget_count = db.scalar(
            select(func.count(Budget.budget_id)).where(
                Budget.analysis_group_id == model.analysis_group_id,
                Budget.status == "active",
            )
        )
        if active_budget_count:
            raise ApiError(
                409,
                "analysis_group_in_use",
                "Archive budgets using this Analysis Group first.",
            )
    model.status = "archived" if archived else "active"
    model.archived_at = datetime.now(UTC) if archived else None
    db.commit()
    return get_analysis_group(db, model.analysis_group_id)


def list_budgets(db: DbSession, include_archived: bool = False) -> list[dict[str, Any]]:
    statement = _budget_statement()
    if not include_archived:
        statement = statement.where(Budget.status == "active")
    return [budget_values(model) for model in db.scalars(statement)]


def get_budget(db: DbSession, budget_id: int) -> Budget:
    model = db.scalar(_budget_statement().where(Budget.budget_id == budget_id))
    if model is None:
        raise ApiError(404, "not_found", "Budget was not found.")
    return model


def create_budget(db: DbSession, payload: BudgetCreate, base_currency: str) -> Budget:
    _validate_budget_payload(db, payload, base_currency)
    values = payload.model_dump(mode="python", exclude={"categories", "tags"})
    model = Budget(**values, normalized_name=normalize_name(payload.name))
    _apply_budget_selection(db, model, payload)
    db.add(model)
    _commit(db, "budget_name_exists")
    return get_budget(db, model.budget_id)


def update_budget(
    db: DbSession, model: Budget, payload: BudgetUpdate, base_currency: str
) -> Budget:
    _validate_budget_payload(db, payload, base_currency)
    values = payload.model_dump(mode="python", exclude={"categories", "tags"})
    for field_name, value in values.items():
        setattr(model, field_name, value)
    model.normalized_name = normalize_name(payload.name)
    _apply_budget_selection(db, model, payload)
    _commit(db, "budget_name_exists")
    return get_budget(db, model.budget_id)


def set_budget_archived(db: DbSession, model: Budget, archived: bool) -> Budget:
    from datetime import UTC, datetime

    if (
        not archived
        and model.analysis_group is not None
        and model.analysis_group.status != "active"
    ):
        raise ApiError(
            409,
            "analysis_group_archived",
            "Restore the linked Analysis Group before restoring this budget.",
        )
    model.status = "archived" if archived else "active"
    model.archived_at = datetime.now(UTC) if archived else None
    db.commit()
    return get_budget(db, model.budget_id)


def budget_outcome(
    db: DbSession,
    model: Budget,
    date_from: date,
    date_to: date,
    base_currency: str,
) -> dict[str, Any]:
    if date_to < date_from:
        raise ApiError(422, "date_range_invalid", "date_to must not precede date_from.")
    selection = compile_budget_selection(db, model)
    active_range = _active_range(model, date_from, date_to)
    matches = (
        _budget_matches(db, selection, *active_range, base_currency)
        if active_range is not None
        else []
    )
    missing_fx_count = (
        _missing_fx_match_count(db, selection, *active_range, base_currency)
        if active_range is not None
        else 0
    )
    actual = sum((item["matched_amount"] for item in matches), Decimal("0")).quantize(MONEY_QUANTUM)
    periods = _periods_for_budget(model, date_from, date_to)
    target = (model.amount * len(periods)).quantize(MONEY_QUANTUM)
    rollover = Decimal("0.0000")
    if model.rollover_mode == "rollover" and periods:
        rollover = _rollover_entering(db, model, selection, periods[0][0], base_currency)
        prior_end = periods[0][0] - timedelta(days=1)
        if prior_end >= model.starts_on:
            missing_fx_count += _missing_fx_match_count(
                db, selection, model.starts_on, prior_end, base_currency
            )
        target = (target + rollover).quantize(MONEY_QUANTUM)
    remaining = (target - actual).quantize(MONEY_QUANTUM)
    consumed = (
        (actual / target * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if target != 0
        else Decimal("0.00")
    )
    overlaps = _overlapping_budget_ids(db, model, date_from, date_to, selection)
    return {
        "budget": budget_values(model),
        "date_from": date_from,
        "date_to": date_to,
        "base_currency": base_currency,
        "target_amount": target,
        "actual_amount": actual,
        "remaining_amount": remaining,
        "consumed_percent": consumed,
        "period_count": len(periods),
        "rollover_adjustment": rollover,
        "matched_transaction_count": len(matches),
        "missing_fx_count": missing_fx_count,
        "overlapping_budget_ids": overlaps,
    }


def budget_transactions(
    db: DbSession,
    model: Budget,
    date_from: date,
    date_to: date,
    base_currency: str,
) -> list[dict[str, Any]]:
    if date_to < date_from:
        raise ApiError(422, "date_range_invalid", "date_to must not precede date_from.")
    selection = compile_budget_selection(db, model)
    active_range = _active_range(model, date_from, date_to)
    if active_range is None:
        return []
    return _budget_matches(db, selection, *active_range, base_currency)


def analysis_group_values(model: AnalysisGroup) -> dict[str, Any]:
    return {
        "analysis_group_id": model.analysis_group_id,
        "name": model.name,
        "notes": model.notes,
        "categories": [
            {
                "category_id": item.category_id,
                "mode": item.selection_mode,
                "include_descendants": item.include_descendants,
            }
            for item in model.categories
        ],
        "tags": [{"tag_id": item.tag_id, "mode": item.selection_mode} for item in model.tags],
        "status": model.status,
        "archived_at": model.archived_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def budget_values(model: Budget) -> dict[str, Any]:
    return {
        "budget_id": model.budget_id,
        "analysis_group_id": model.analysis_group_id,
        "name": model.name,
        "amount": model.amount,
        "currency": model.currency,
        "period_type": model.period_type,
        "rollover_mode": model.rollover_mode,
        "starts_on": model.starts_on,
        "ends_on": model.ends_on,
        "anchor_day": model.anchor_day,
        "notes": model.notes,
        "categories": [
            {
                "category_id": item.category_id,
                "mode": item.selection_mode,
                "include_descendants": item.include_descendants,
            }
            for item in model.categories
        ],
        "tags": [{"tag_id": item.tag_id, "mode": item.selection_mode} for item in model.tags],
        "status": model.status,
        "archived_at": model.archived_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def compile_budget_selection(db: DbSession, model: Budget) -> CompiledSelection:
    category_rows = list(model.categories)
    tag_rows = list(model.tags)
    if model.analysis_group is not None:
        category_rows.extend(model.analysis_group.categories)
        tag_rows.extend(model.analysis_group.tags)
    include_categories: set[int] = set()
    exclude_categories: set[int] = set()
    for item in category_rows:
        target = include_categories if item.selection_mode == "include" else exclude_categories
        target.add(item.category_id)
        if item.include_descendants:
            target.update(_category_descendants(db, item.category_id))
    return CompiledSelection(
        include_categories=frozenset(include_categories),
        exclude_categories=frozenset(exclude_categories),
        include_tags=frozenset(
            item.tag_id for item in tag_rows if item.selection_mode == "include"
        ),
        exclude_tags=frozenset(
            item.tag_id for item in tag_rows if item.selection_mode == "exclude"
        ),
    )


def _budget_matches(
    db: DbSession,
    selection: CompiledSelection,
    date_from: date,
    date_to: date,
    base_currency: str,
) -> list[dict[str, Any]]:
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.status == "active",
                Transaction.transaction_kind.in_(("expense", "refund", "reimbursement")),
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.base_currency == base_currency,
                Transaction.converted_amount.is_not(None),
            )
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
            .order_by(Transaction.transaction_date.desc(), Transaction.transaction_id.desc())
        )
    )
    links = _linked_expense_ids(db, [item.transaction_id for item in transactions])
    original_ids = set(links.values())
    originals = {
        item.transaction_id: item
        for item in db.scalars(
            select(Transaction)
            .where(Transaction.transaction_id.in_(original_ids))
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        )
    }
    results: list[dict[str, Any]] = []
    for transaction in transactions:
        assert transaction.converted_amount is not None
        if transaction.transaction_kind == "expense":
            components = [
                (split, split.converted_amount)
                for split in transaction.splits
                if split.converted_amount is not None
            ]
            sign = Decimal("1")
        else:
            components = allocate_recovery_to_splits(
                originals[links[transaction.transaction_id]], transaction.converted_amount
            )
            sign = Decimal("-1")
        matched = sum(
            (amount for split, amount in components if _selection_matches(split, selection)),
            Decimal("0"),
        ).quantize(MONEY_QUANTUM)
        if matched == 0:
            continue
        results.append(
            {
                "transaction_id": transaction.transaction_id,
                "transaction_date": transaction.transaction_date,
                "description": transaction.description,
                "transaction_kind": transaction.transaction_kind,
                "matched_amount": (sign * matched).quantize(MONEY_QUANTUM),
                "base_currency": base_currency,
            }
        )
    return results


def _selection_matches(split: TransactionSplit, selection: CompiledSelection) -> bool:
    tag_ids = {tag.tag_id for tag in split.tags}
    return (
        (not selection.include_categories or split.category_id in selection.include_categories)
        and split.category_id not in selection.exclude_categories
        and (not selection.include_tags or bool(tag_ids & selection.include_tags))
        and not bool(tag_ids & selection.exclude_tags)
    )


def _missing_fx_match_count(
    db: DbSession,
    selection: CompiledSelection,
    date_from: date,
    date_to: date,
    base_currency: str,
) -> int:
    transactions = list(
        db.scalars(
            select(Transaction)
            .where(
                Transaction.status == "active",
                Transaction.transaction_kind.in_(("expense", "refund", "reimbursement")),
                Transaction.transaction_date >= date_from,
                Transaction.transaction_date <= date_to,
                Transaction.base_currency == base_currency,
                Transaction.converted_amount.is_(None),
            )
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        )
    )
    links = _linked_expense_ids(db, [item.transaction_id for item in transactions])
    original_ids = set(links.values())
    originals = {
        item.transaction_id: item
        for item in db.scalars(
            select(Transaction)
            .where(Transaction.transaction_id.in_(original_ids))
            .options(selectinload(Transaction.splits).selectinload(TransactionSplit.tags))
        )
    }
    count = 0
    for transaction in transactions:
        source = (
            transaction
            if transaction.transaction_kind == "expense"
            else originals.get(links.get(transaction.transaction_id, 0))
        )
        if source is not None and any(
            _selection_matches(split, selection) for split in source.splits
        ):
            count += 1
    return count


def _periods_for_budget(model: Budget, date_from: date, date_to: date) -> list[tuple[date, date]]:
    active_range = _active_range(model, date_from, date_to)
    if active_range is None:
        return []
    active_from, active_to = active_range
    if model.period_type == "custom":
        return [(model.starts_on, model.ends_on or model.starts_on)]
    periods: list[tuple[date, date]] = []
    cursor = _period_start(model, active_from)
    while cursor <= active_to:
        end = _next_period_start(model, cursor) - timedelta(days=1)
        if end >= active_from and cursor <= active_to:
            periods.append((cursor, end))
        cursor = end + timedelta(days=1)
    return periods


def _active_range(model: Budget, date_from: date, date_to: date) -> tuple[date, date] | None:
    active_from = max(date_from, model.starts_on)
    active_to = min(date_to, model.ends_on) if model.ends_on is not None else date_to
    return None if active_to < active_from else (active_from, active_to)


def _period_start(model: Budget, value: date) -> date:
    if model.period_type == "calendar_month":
        return date(value.year, value.month, 1)
    if model.period_type == "calendar_year":
        return date(value.year, 1, 1)
    anchor = model.anchor_day
    candidate = date(value.year, value.month, anchor)
    if candidate > value:
        year, month = _shift_month(value.year, value.month, -1)
        candidate = date(year, month, anchor)
    return candidate


def _next_period_start(model: Budget, value: date) -> date:
    if model.period_type == "calendar_year":
        return date(value.year + 1, 1, 1)
    year, month = _shift_month(value.year, value.month, 1)
    day = 1 if model.period_type == "calendar_month" else model.anchor_day
    return date(year, month, day)


def _rollover_entering(
    db: DbSession,
    model: Budget,
    selection: CompiledSelection,
    selected_start: date,
    base_currency: str,
) -> Decimal:
    prior_end = selected_start - timedelta(days=1)
    periods = _periods_for_budget(model, model.starts_on, prior_end)
    if not periods:
        return Decimal("0.0000")
    actual = sum(
        (
            item["matched_amount"]
            for item in _budget_matches(db, selection, model.starts_on, prior_end, base_currency)
        ),
        Decimal("0"),
    )
    return (model.amount * len(periods) - actual).quantize(MONEY_QUANTUM)


def _overlapping_budget_ids(
    db: DbSession,
    model: Budget,
    date_from: date,
    date_to: date,
    selection: CompiledSelection,
) -> list[int]:
    candidates = list(
        db.scalars(
            _budget_statement().where(
                Budget.budget_id != model.budget_id,
                Budget.status == "active",
                Budget.starts_on <= date_to,
                (Budget.ends_on.is_(None) | (Budget.ends_on >= date_from)),
            )
        )
    )
    return [
        candidate.budget_id
        for candidate in candidates
        if _selections_may_overlap(selection, compile_budget_selection(db, candidate))
    ]


def _selections_may_overlap(first: CompiledSelection, second: CompiledSelection) -> bool:
    categories_overlap = (
        not first.include_categories
        or not second.include_categories
        or bool(first.include_categories & second.include_categories)
    )
    tags_overlap = (
        not first.include_tags
        or not second.include_tags
        or bool(first.include_tags & second.include_tags)
    )
    return categories_overlap and tags_overlap


def _category_descendants(db: DbSession, category_id: int) -> set[int]:
    descendants: set[int] = set()
    frontier = {category_id}
    while frontier:
        children = set(
            db.scalars(
                select(Category.category_id).where(Category.parent_category_id.in_(frontier))
            )
        )
        children -= descendants
        descendants.update(children)
        frontier = children
    return descendants


def _apply_group_selection(
    db: DbSession, model: AnalysisGroup, payload: AnalysisGroupCreate
) -> None:
    _validate_selection_records(db, payload.categories, payload.tags)
    model.categories = [
        AnalysisGroupCategory(
            category_id=item.category_id,
            selection_mode=item.mode.value,
            include_descendants=item.include_descendants,
        )
        for item in payload.categories
    ]
    model.tags = [
        AnalysisGroupTag(tag_id=item.tag_id, selection_mode=item.mode.value)
        for item in payload.tags
    ]


def _apply_budget_selection(db: DbSession, model: Budget, payload: BudgetCreate) -> None:
    _validate_selection_records(db, payload.categories, payload.tags)
    model.categories = [
        BudgetCategory(
            category_id=item.category_id,
            selection_mode=item.mode.value,
            include_descendants=item.include_descendants,
        )
        for item in payload.categories
    ]
    model.tags = [
        BudgetTag(tag_id=item.tag_id, selection_mode=item.mode.value) for item in payload.tags
    ]


def _validate_selection_records(db: DbSession, categories, tags) -> None:
    for selection in categories:
        category = db.get(Category, selection.category_id)
        if category is None or category.status != "active" or category.category_kind != "expense":
            raise ApiError(
                422, "budget_category_invalid", "Budgets require active expense categories."
            )
    for selection in tags:
        tag = db.get(Tag, selection.tag_id)
        if tag is None or tag.status != "active":
            raise ApiError(422, "budget_tag_invalid", "Budgets require active tags.")


def _validate_budget_payload(db: DbSession, payload: BudgetCreate, base_currency: str) -> None:
    if payload.currency != base_currency:
        raise ApiError(422, "budget_currency_mismatch", "Budget currency must equal base currency.")
    if payload.analysis_group_id is not None:
        group = get_analysis_group(db, payload.analysis_group_id)
        if group.status != "active":
            raise ApiError(422, "analysis_group_archived", "Budget Analysis Group is archived.")


def _group_statement():
    return (
        select(AnalysisGroup)
        .options(selectinload(AnalysisGroup.categories), selectinload(AnalysisGroup.tags))
        .order_by(AnalysisGroup.status, AnalysisGroup.normalized_name)
    )


def _budget_statement():
    return (
        select(Budget)
        .options(
            selectinload(Budget.categories),
            selectinload(Budget.tags),
            selectinload(Budget.analysis_group).selectinload(AnalysisGroup.categories),
            selectinload(Budget.analysis_group).selectinload(AnalysisGroup.tags),
        )
        .order_by(Budget.status, Budget.normalized_name)
    )


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    value = year * 12 + month - 1 + delta
    return value // 12, value % 12 + 1


def _commit(db: DbSession, code: str) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApiError(409, code, "The budget operation conflicts with existing data.") from error
