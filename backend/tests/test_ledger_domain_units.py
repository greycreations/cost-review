from datetime import date

import pytest
from pydantic import ValidationError

from app.ledger_schemas import TransactionCreate
from app.transaction_services import _comparison_period


def transaction_payload(**overrides):
    payload = {
        "account_id": 1,
        "transaction_kind": "expense",
        "transaction_date": "2026-08-12",
        "posting_date": "2026-08-12",
        "description": "Mixed purchase",
        "original_amount": "1000.0000",
        "original_currency": "sek",
        "splits": [
            {"original_amount": "600.0000", "category_id": 1},
            {"original_amount": "400.0000", "category_id": 2},
        ],
    }
    payload.update(overrides)
    return payload


def test_split_transaction_requires_exact_decimal_allocation() -> None:
    model = TransactionCreate.model_validate(transaction_payload())

    assert model.original_currency == "SEK"
    assert model.splits is not None
    assert sum(split.original_amount for split in model.splits) == model.original_amount

    with pytest.raises(ValidationError, match="split amounts must equal"):
        TransactionCreate.model_validate(
            transaction_payload(
                splits=[
                    {"original_amount": "600.0000", "category_id": 1},
                    {"original_amount": "399.9999", "category_id": 2},
                ]
            )
        )


def test_split_transaction_rejects_header_classification() -> None:
    with pytest.raises(ValidationError, match="classification on their splits"):
        TransactionCreate.model_validate(transaction_payload(category_id=1))


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("previous_period", (date(2026, 7, 1), date(2026, 7, 31))),
        ("previous_year", (date(2025, 8, 1), date(2025, 8, 31))),
    ],
)
def test_comparison_periods_are_stable(mode: str, expected: tuple[date, date]) -> None:
    assert _comparison_period(date(2026, 8, 1), date(2026, 8, 31), mode) == expected


def test_previous_year_handles_leap_day() -> None:
    assert _comparison_period(
        date(2024, 2, 29), date(2024, 2, 29), "previous_year"
    ) == (date(2023, 2, 28), date(2023, 2, 28))
