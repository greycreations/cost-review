from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.ledger_schemas import Name160, Notes

Money = Annotated[Decimal, Field(gt=0, max_digits=20, decimal_places=4)]


class RecurringCreate(BaseModel):
    name: Name160
    account_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)
    transaction_kind: Literal["expense", "income"]
    amount: Money
    amount_type: Literal["fixed", "variable"] = "fixed"
    currency: str | None = None
    frequency: Literal["weekly", "monthly", "quarterly", "yearly"] = "monthly"
    interval_count: int = Field(default=1, ge=1, le=52)
    start_date: date
    end_date: date | None = None
    tolerance_percent: Decimal = Field(default=Decimal("10"), ge=0, le=100, decimal_places=4)
    notes: Notes | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if isinstance(value, str) else value


class RecurringUpdate(BaseModel):
    name: Name160 | None = None
    provider_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)
    end_date: date | None = None
    tolerance_percent: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=4)
    notes: Notes | None = None


class RecurringAmountChange(BaseModel):
    effective_from: date
    amount: Money
    amount_type: Literal["fixed", "variable"] = "fixed"


class RecurringVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    effective_from: date
    amount: Decimal
    amount_type: str


class RecurringRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    recurring_definition_id: int
    name: str
    account_id: int
    provider_id: int | None
    category_id: int | None
    transaction_kind: str
    currency: str
    frequency: str
    interval_count: int
    start_date: date
    end_date: date | None
    tolerance_percent: Decimal
    notes: str | None
    versions: list[RecurringVersionRead]
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RecurringCandidate(BaseModel):
    transaction_id: int
    transaction_date: date
    description: str
    amount: Decimal
    confidence: int


class ExpectedOccurrenceRead(BaseModel):
    recurring_definition_id: int
    name: str
    account_id: int
    transaction_kind: str
    due_date: date
    expected_amount: Decimal
    amount_type: str
    currency: str
    status: Literal["expected", "overdue", "confirmed", "skipped"]
    transaction_id: int | None
    deviation_percent: Decimal | None
    outside_tolerance: bool
    candidates: list[RecurringCandidate]


class OccurrenceConfirm(BaseModel):
    """Confirm by linking an existing transaction or by recording a new one."""

    transaction_id: int | None = Field(default=None, gt=0)
    amount: Money | None = None
    transaction_date: date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=240)
