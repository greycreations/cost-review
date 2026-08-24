from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import (
    AmountType,
    ExpenseStatus,
    ExpenseType,
    MasterDataStatus,
    PaymentMethod,
    RecurrenceUnit,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProviderRead(ApiModel):
    provider_id: int
    name: str
    website: str | None
    notes: str | None
    status: MasterDataStatus
    created_at: datetime
    updated_at: datetime


class CategoryRead(ApiModel):
    category_id: int
    name: str
    description: str | None
    status: MasterDataStatus
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ExpenseRead(ApiModel):
    expense_id: int
    name: str
    provider_id: int | None
    category_id: int
    amount: Decimal
    currency: str
    amount_type: AmountType
    recurrence_unit: RecurrenceUnit | None
    recurrence_interval: int | None
    expense_type: ExpenseType
    start_date: date | None
    end_date: date | None
    next_payment_date: date | None
    payment_method: PaymentMethod | None
    status: ExpenseStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class HealthRead(BaseModel):
    status: str
    database: str
