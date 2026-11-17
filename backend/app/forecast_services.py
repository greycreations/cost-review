from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budget_services import budget_outcome, budget_transactions
from app.models import Budget
from app.transaction_services import _ledger_analysis_period, ledger_summary

ZERO = Decimal("0.0000")
HISTORY_MONTHS = 3


def month_expense_forecast(
    db: Session,
    as_of: date,
    base_currency: str,
    **filters: Any,
) -> dict[str, object]:
    first = as_of.replace(day=1)
    last = as_of.replace(day=monthrange(as_of.year, as_of.month)[1])
    actual = _ledger_analysis_period(db, first, as_of, base_currency, **filters)
    expenses = sum((day["expenses"] for day in actual["daily"]), ZERO)
    missing_fx = ledger_summary(db, first, as_of, base_currency, **filters)["missing_fx_count"]
    history_ranges = _preceding_months(first)
    samples = []
    for start, end in history_ranges:
        summary = ledger_summary(db, start, end, base_currency, **filters)
        if summary["missing_fx_count"]:
            continue
        history = _ledger_analysis_period(db, start, end, base_currency, **filters)
        if any(day["expenses"] > 0 for day in history["daily"]):
            samples.append(
                sum(
                    (day["expenses"] for day in history["daily"] if day["date"].day > as_of.day),
                    ZERO,
                )
            )

    projected_remaining = None
    if not missing_fx:
        if as_of == last:
            projected_remaining = ZERO
        elif len(samples) == HISTORY_MONTHS:
            projected_remaining = median(samples)
    budget_risks = []
    if not any(value is not None for key, value in filters.items() if key != "perspective"):
        budget_risks = _budget_risks(
            db,
            first,
            as_of,
            last,
            history_ranges,
            base_currency,
            filters.get("perspective", "total"),
        )
    return {
        "date_from": first,
        "date_to": last,
        "as_of": as_of,
        "base_currency": base_currency,
        "history_month_count": len(samples),
        "missing_fx_count": missing_fx,
        "actual_expenses": expenses,
        "forecast_expenses": (
            expenses + projected_remaining if projected_remaining is not None else None
        ),
        "budget_risks": budget_risks,
    }


def _preceding_months(first: date) -> list[tuple[date, date]]:
    ranges = []
    for _ in range(HISTORY_MONTHS):
        end = first - timedelta(days=1)
        first = end.replace(day=1)
        ranges.append((first, end))
    return ranges


def _budget_risks(
    db: Session,
    first: date,
    as_of: date,
    last: date,
    history_ranges: list[tuple[date, date]],
    base_currency: str,
    perspective: str,
) -> list[dict[str, object]]:
    budgets = db.scalars(
        select(Budget).where(
            Budget.status == "active",
            Budget.period_type == "calendar_month",
            Budget.starts_on <= history_ranges[-1][0],
            (Budget.ends_on.is_(None) | (Budget.ends_on >= last)),
            Budget.currency == base_currency,
        )
    )
    risks = []
    for budget in budgets:
        current = budget_outcome(db, budget, first, as_of, base_currency, perspective)
        if current["missing_fx_count"]:
            continue
        samples = []
        for start, end in history_ranges if as_of < last else []:
            history = budget_outcome(db, budget, start, end, base_currency, perspective)
            if history["missing_fx_count"] or not history["matched_transaction_count"]:
                break
            rows = budget_transactions(db, budget, start, end, base_currency, perspective)
            samples.append(
                sum(
                    (
                        row["matched_amount"]
                        for row in rows
                        if row["transaction_date"].day > as_of.day
                    ),
                    ZERO,
                )
            )
        if as_of < last and len(samples) != HISTORY_MONTHS:
            continue
        projected = current["actual_amount"] + (median(samples) if samples else ZERO)
        target = current["target_amount"]
        if projected > target:
            risks.append(
                {
                    "budget_id": budget.budget_id,
                    "name": budget.name,
                    "actual_amount": current["actual_amount"],
                    "target_amount": target,
                    "forecast_amount": projected,
                    "overrun": projected - target,
                }
            )
    return sorted(risks, key=lambda item: (-item["overrun"], item["budget_id"]))
