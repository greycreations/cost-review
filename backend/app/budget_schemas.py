from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from app.models import BudgetPeriodType, BudgetRolloverMode, LifecycleStatus, SelectionMode

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]


class CategorySelection(BaseModel):
    category_id: int = Field(gt=0)
    mode: SelectionMode = SelectionMode.INCLUDE
    include_descendants: bool = True


class TagSelection(BaseModel):
    tag_id: int = Field(gt=0)
    mode: SelectionMode = SelectionMode.INCLUDE


class AccountSelection(BaseModel):
    account_id: int = Field(gt=0)
    mode: SelectionMode = SelectionMode.INCLUDE


class ProviderSelection(BaseModel):
    provider_id: int = Field(gt=0)
    mode: SelectionMode = SelectionMode.INCLUDE


class SelectionInput(BaseModel):
    categories: list[CategorySelection] = Field(default_factory=list, max_length=100)
    tags: list[TagSelection] = Field(default_factory=list, max_length=100)
    accounts: list[AccountSelection] = Field(default_factory=list, max_length=100)
    providers: list[ProviderSelection] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_selections(self) -> SelectionInput:
        category_keys = [(item.category_id, item.mode) for item in self.categories]
        tag_keys = [(item.tag_id, item.mode) for item in self.tags]
        account_keys = [(item.account_id, item.mode) for item in self.accounts]
        provider_keys = [(item.provider_id, item.mode) for item in self.providers]
        if len(category_keys) != len(set(category_keys)):
            raise ValueError("category selections must be unique per mode")
        if len(tag_keys) != len(set(tag_keys)):
            raise ValueError("tag selections must be unique per mode")
        if len(account_keys) != len(set(account_keys)):
            raise ValueError("account selections must be unique per mode")
        if len(provider_keys) != len(set(provider_keys)):
            raise ValueError("provider selections must be unique per mode")
        return self


class AnalysisGroupCreate(SelectionInput):
    name: Name
    notes: Notes | None = None


class AnalysisGroupUpdate(SelectionInput):
    name: Name
    notes: Notes | None = None


class AnalysisGroupRead(BaseModel):
    analysis_group_id: int
    name: str
    notes: str | None
    categories: list[CategorySelection]
    tags: list[TagSelection]
    accounts: list[AccountSelection]
    providers: list[ProviderSelection]
    status: LifecycleStatus
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BudgetCreate(SelectionInput):
    name: Name
    amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    currency: CurrencyCode
    period_type: BudgetPeriodType = BudgetPeriodType.CALENDAR_MONTH
    rollover_mode: BudgetRolloverMode = BudgetRolloverMode.RESET
    starts_on: date
    ends_on: date | None = None
    anchor_day: int = Field(default=25, ge=1, le=28)
    analysis_group_id: int | None = Field(default=None, gt=0)
    notes: Notes | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_period(self) -> BudgetCreate:
        if self.ends_on is not None and self.ends_on < self.starts_on:
            raise ValueError("ends_on must not precede starts_on")
        if self.period_type == BudgetPeriodType.CUSTOM and self.ends_on is None:
            raise ValueError("custom budgets require ends_on")
        if (
            self.period_type == BudgetPeriodType.CUSTOM
            and self.rollover_mode == BudgetRolloverMode.ROLLOVER
        ):
            raise ValueError("custom budgets cannot roll over")
        return self


class BudgetUpdate(BudgetCreate):
    pass


class BudgetRead(BaseModel):
    budget_id: int
    analysis_group_id: int | None
    name: str
    amount: Decimal
    currency: str
    period_type: BudgetPeriodType
    rollover_mode: BudgetRolloverMode
    starts_on: date
    ends_on: date | None
    anchor_day: int
    notes: str | None
    categories: list[CategorySelection]
    tags: list[TagSelection]
    accounts: list[AccountSelection]
    providers: list[ProviderSelection]
    status: LifecycleStatus
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BudgetOutcomeRead(BaseModel):
    budget: BudgetRead
    date_from: date
    date_to: date
    base_currency: str
    perspective: Literal["total", "my_share"]
    target_amount: Decimal
    actual_amount: Decimal
    remaining_amount: Decimal
    consumed_percent: Decimal
    period_count: int
    rollover_adjustment: Decimal
    matched_transaction_count: int
    missing_fx_count: int
    overlapping_budget_ids: list[int]


class BudgetTransactionRead(BaseModel):
    transaction_id: int
    transaction_date: date
    description: str
    transaction_kind: str
    matched_amount: Decimal
    base_currency: str


class BudgetTrendPointRead(BaseModel):
    period_start: date
    period_end: date
    target_amount: Decimal
    actual_amount: Decimal
    remaining_amount: Decimal
    consumed_percent: Decimal
    missing_fx_count: int


class BudgetTrendRead(BaseModel):
    budget_id: int
    base_currency: str
    perspective: Literal["total", "my_share"]
    points: list[BudgetTrendPointRead]
