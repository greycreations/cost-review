"""Property-based checks of the money rules every analysis depends on.

Example tests prove chosen scenarios. These generate many inputs and check the
invariants that must hold for all of them: nothing is created or lost when an
amount is divided, and interpretation of amounts is exact.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from app.import_parsing import parse_amount
from app.models import Transaction, TransactionSplit, TransactionSplitShare
from app.recurring_services import add_months
from app.sharing import TOTAL, Perspective, share_multiplier
from app.transaction_services import MONEY_QUANTUM, allocate_recovery_to_splits

money = st.decimals(
    min_value=Decimal("0.01"),
    max_value=Decimal("1000000"),
    places=2,
    allow_nan=False,
    allow_infinity=False,
)


@st.composite
def percentage_allocations(draw) -> list[Decimal]:
    """Whole-hundredth percentages that always total exactly 100."""

    count = draw(st.integers(min_value=1, max_value=6))
    cuts = sorted(draw(st.lists(st.integers(1, 9999), min_size=count - 1, max_size=count - 1)))
    bounds = [0, *cuts, 10000]
    return [Decimal(bounds[i + 1] - bounds[i]) / Decimal(100) for i in range(count)]


def split_with(percentages: list[Decimal]) -> TransactionSplit:
    split = TransactionSplit(original_amount=Decimal("100"), converted_amount=Decimal("100"))
    split.share_allocations = [
        TransactionSplitShare(sharing_party_id=index + 1, percentage=percentage)
        for index, percentage in enumerate(percentages)
    ]
    return split


@given(percentage_allocations())
def test_every_members_share_adds_up_to_the_whole(percentages: list[Decimal]) -> None:
    split = split_with(percentages)
    shares = [
        share_multiplier(split, Perspective(kind="my_share", self_party_id=index + 1))
        for index in range(len(percentages))
    ]
    assert sum(shares, Decimal("0")) == Decimal("1")
    assert all(Decimal("0") <= share <= Decimal("1") for share in shares)
    assert share_multiplier(split, TOTAL) == Decimal("1")


@given(st.lists(money, min_size=1, max_size=8), money)
def test_a_recovery_is_divided_over_splits_without_creating_or_losing_money(
    split_amounts: list[Decimal], recovery: Decimal
) -> None:
    original = Transaction()
    original.splits = [
        TransactionSplit(original_amount=amount, converted_amount=amount)
        for amount in split_amounts
    ]
    recovery = recovery.quantize(MONEY_QUANTUM)
    allocations = allocate_recovery_to_splits(original, recovery)

    assert len(allocations) == len(split_amounts)
    assert sum((amount for _, amount in allocations), Decimal("0")) == recovery
    total = sum(split_amounts, Decimal("0"))
    for (split, amount), weight in zip(allocations[:-1], split_amounts[:-1], strict=True):
        assert split.converted_amount == weight
        assert abs(amount - recovery * weight / total) <= MONEY_QUANTUM


@given(
    st.decimals(
        min_value=Decimal("-99999999"),
        max_value=Decimal("99999999"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    )
)
def test_swedish_and_english_amount_formats_are_read_exactly(value: Decimal) -> None:
    sign = "-" if value < 0 else ""
    whole, fraction = f"{abs(value):.2f}".split(".")
    groups = f"{int(whole):,}"
    swedish = f"{sign}{groups.replace(',', ' ')},{fraction}"
    english = f"{sign}{groups}.{fraction}"

    assert parse_amount(swedish, ",") == value
    assert parse_amount(english, ".") == value
    assert parse_amount(f"{swedish} kr", ",") == value


@settings(max_examples=300)
@given(
    st.dates(min_value=date(2000, 1, 1), max_value=date(2090, 12, 31)),
    st.integers(min_value=0, max_value=240),
)
def test_monthly_schedules_never_drift_from_their_anchor_day(start: date, months: int) -> None:
    due = add_months(start, months, start.day)
    expected_month = (start.month - 1 + months) % 12 + 1
    assert due.month == expected_month
    assert due.day == min(start.day, calendar.monthrange(due.year, due.month)[1])
