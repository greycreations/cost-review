from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_type]


class MasterDataStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AmountType(StrEnum):
    EXACT = "exact"
    ESTIMATED = "estimated"


class RecurrenceUnit(StrEnum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class ExpenseType(StrEnum):
    RECURRING = "recurring"
    ONE_TIME = "one_time"


class PaymentMethod(StrEnum):
    INVOICE = "invoice"
    DIRECT_DEBIT = "direct_debit"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    OTHER = "other"


class ExpenseStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class Provider(TimestampMixin, Base):
    __tablename__ = "providers"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="provider_status_allowed",
        ),
        Index("ix_providers_name", "name"),
    )

    provider_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MasterDataStatus] = mapped_column(
        Enum(
            MasterDataStatus,
            values_callable=enum_values,
            name="provider_status",
            native_enum=False,
            create_constraint=False,
            length=8,
        ),
        default=MasterDataStatus.ACTIVE,
        server_default=MasterDataStatus.ACTIVE.value,
    )

    expenses: Mapped[list[Expense]] = relationship(back_populates="provider")


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        CheckConstraint(
            "status IN ('active', 'archived')",
            name="category_status_allowed",
        ),
        Index("ix_categories_name", "name"),
    )

    category_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[MasterDataStatus] = mapped_column(
        Enum(
            MasterDataStatus,
            values_callable=enum_values,
            name="category_status",
            native_enum=False,
            create_constraint=False,
            length=8,
        ),
        default=MasterDataStatus.ACTIVE,
        server_default=MasterDataStatus.ACTIVE.value,
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    expenses: Mapped[list[Expense]] = relationship(back_populates="category")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="amount_non_negative"),
        CheckConstraint(
            "amount_type IN ('exact', 'estimated')",
            name="amount_type_allowed",
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="date_order",
        ),
        CheckConstraint(
            "(expense_type = 'one_time' AND recurrence_unit IS NULL "
            "AND recurrence_interval IS NULL) OR "
            "(expense_type = 'recurring' AND recurrence_unit IS NOT NULL "
            "AND recurrence_interval > 0)",
            name="recurrence_shape",
        ),
        CheckConstraint(
            "recurrence_unit IS NULL OR recurrence_unit IN ('day', 'week', 'month', 'year')",
            name="recurrence_unit_allowed",
        ),
        CheckConstraint(
            "expense_type IN ('recurring', 'one_time')",
            name="expense_type_allowed",
        ),
        CheckConstraint(
            "payment_method IS NULL OR payment_method IN "
            "('invoice', 'direct_debit', 'credit_card', 'bank_transfer', 'other')",
            name="payment_method_allowed",
        ),
        CheckConstraint(
            "status IN ('active', 'paused', 'ended')",
            name="expense_status_allowed",
        ),
        Index("ix_expenses_name", "name"),
        Index("ix_expenses_provider_id", "provider_id"),
        Index("ix_expenses_category_id", "category_id"),
        Index("ix_expenses_status", "status"),
    )

    expense_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="SET NULL")
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), default="SEK", server_default="SEK")
    amount_type: Mapped[AmountType] = mapped_column(
        Enum(
            AmountType,
            values_callable=enum_values,
            name="amount_type",
            native_enum=False,
            create_constraint=False,
            length=9,
        ),
        default=AmountType.EXACT,
        server_default=AmountType.EXACT.value,
    )
    recurrence_unit: Mapped[RecurrenceUnit | None] = mapped_column(
        Enum(
            RecurrenceUnit,
            values_callable=enum_values,
            name="recurrence_unit",
            native_enum=False,
            create_constraint=False,
            length=5,
        )
    )
    recurrence_interval: Mapped[int | None] = mapped_column(Integer)
    expense_type: Mapped[ExpenseType] = mapped_column(
        Enum(
            ExpenseType,
            values_callable=enum_values,
            name="expense_type",
            native_enum=False,
            create_constraint=False,
            length=9,
        ),
        default=ExpenseType.RECURRING,
        server_default=ExpenseType.RECURRING.value,
    )
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    next_payment_date: Mapped[date | None] = mapped_column(Date)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(
            PaymentMethod,
            values_callable=enum_values,
            name="payment_method",
            native_enum=False,
            create_constraint=False,
            length=13,
        )
    )
    status: Mapped[ExpenseStatus] = mapped_column(
        Enum(
            ExpenseStatus,
            values_callable=enum_values,
            name="expense_status",
            native_enum=False,
            create_constraint=False,
            length=6,
        ),
        default=ExpenseStatus.ACTIVE,
        server_default=ExpenseStatus.ACTIVE.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)

    provider: Mapped[Provider | None] = relationship(back_populates="expenses")
    category: Mapped[Category] = relationship(back_populates="expenses")
