from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ArchiveMixin:
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EnvironmentKind(StrEnum):
    PRODUCTION = "production"
    TEST = "test"


class Language(StrEnum):
    SWEDISH = "sv"
    ENGLISH = "en"


class WeekStart(StrEnum):
    MONDAY = "monday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class DateFormat(StrEnum):
    ISO = "YYYY-MM-DD"
    DAY_FIRST = "DD/MM/YYYY"
    MONTH_FIRST = "MM/DD/YYYY"


class NumberFormat(StrEnum):
    SPACE_COMMA = "space-comma"
    COMMA_DOT = "comma-dot"
    DOT_COMMA = "dot-comma"


class LifecycleStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AccountType(StrEnum):
    CURRENT = "current"
    SAVINGS = "savings"
    CREDIT_CARD = "credit_card"
    INVESTMENT = "investment"
    LOAN_DEBT = "loan_debt"
    VALUE_BASED = "value_based"
    CASH = "cash"
    OTHER = "other"


class CategoryKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    TRANSFER = "transfer"
    REFUND = "refund"
    REIMBURSEMENT = "reimbursement"
    ADJUSTMENT = "adjustment"
    INVESTMENT_TRADE = "investment_trade"


class TransactionSource(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"
    RECURRING = "recurring"
    SYSTEM = "system"


class TransferPurpose(StrEnum):
    INTERNAL = "internal"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    CREDIT_CARD_PAYMENT = "credit_card_payment"
    DEBT_REPAYMENT = "debt_repayment"


class FxRateStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    MANUAL = "manual"
    AUTOMATIC = "automatic"
    MISSING = "missing"


class BudgetPeriodType(StrEnum):
    CALENDAR_MONTH = "calendar_month"
    SALARY_CYCLE = "salary_cycle"
    CALENDAR_YEAR = "calendar_year"
    CUSTOM = "custom"


class BudgetRolloverMode(StrEnum):
    RESET = "reset"
    ROLLOVER = "rollover"


class SelectionMode(StrEnum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


class AdjustmentDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class EnvironmentMetadata(Base):
    __tablename__ = "environment_metadata"
    __table_args__ = (
        CheckConstraint("metadata_id = 1", name="singleton"),
        CheckConstraint("environment IN ('production', 'test')", name="environment_allowed"),
        CheckConstraint("reset_generation >= 0", name="reset_generation_non_negative"),
    )

    metadata_id: Mapped[int] = mapped_column(
        SmallInteger, primary_key=True, default=1, autoincrement=False
    )
    environment: Mapped[str] = mapped_column(String(10))
    data_plane_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), unique=True)
    reset_generation: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    initialized_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('created', 'updated', 'archived', 'restored', "
            "'balance_adjusted', 'permanently_deleted')",
            name="action_allowed",
        ),
        CheckConstraint(
            "change_source IN ('user', 'system', 'import', 'restore')",
            name="change_source_allowed",
        ),
        Index("ix_audit_events_entity", "entity_type", "entity_id", "created_at"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    audit_event_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    action: Mapped[str] = mapped_column(String(32))
    change_source: Mapped[str] = mapped_column(String(16), default="user")
    changes: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_normalized_username", "normalized_username", unique=True),)

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64))
    normalized_username: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(512))

    settings: Mapped[AppSettings] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AppSettings(TimestampMixin, Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint("language IN ('sv', 'en')", name="language_allowed"),
        CheckConstraint(
            "date_format IN ('YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY')",
            name="date_format_allowed",
        ),
        CheckConstraint(
            "number_format IN ('space-comma', 'comma-dot', 'dot-comma')",
            name="number_format_allowed",
        ),
        CheckConstraint(
            "week_start IN ('monday', 'saturday', 'sunday')", name="week_start_allowed"
        ),
        CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso_shape"),
    )

    settings_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), unique=True
    )
    language: Mapped[str] = mapped_column(String(2), default="sv", server_default="sv")
    region: Mapped[str] = mapped_column(String(16), default="SE", server_default="SE")
    base_currency: Mapped[str] = mapped_column(String(3), default="SEK", server_default="SEK")
    timezone: Mapped[str] = mapped_column(
        String(64), default="Europe/Stockholm", server_default="Europe/Stockholm"
    )
    date_format: Mapped[str] = mapped_column(
        String(10), default="YYYY-MM-DD", server_default="YYYY-MM-DD"
    )
    number_format: Mapped[str] = mapped_column(
        String(16), default="space-comma", server_default="space-comma"
    )
    week_start: Mapped[str] = mapped_column(
        String(10), default="monday", server_default="monday"
    )

    user: Mapped[User] = relationship(back_populates="settings")


class Session(Base):
    __tablename__ = "sessions"
    __table_args__ = (Index("ix_sessions_expires_at", "expires_at"),)

    session_token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"))
    csrf_token_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class Account(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "account_type IN ('current', 'savings', 'credit_card', 'investment', "
            "'loan_debt', 'value_based', 'cash', 'other')",
            name="account_type_allowed",
        ),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_shape"),
        CheckConstraint(
            "interest_rate IS NULL OR interest_rate BETWEEN -100 AND 1000",
            name="interest_rate_reasonable",
        ),
        CheckConstraint(
            "lock_end_date IS NULL OR lock_start_date IS NOT NULL",
            name="lock_end_requires_start",
        ),
        CheckConstraint(
            "lock_end_date IS NULL OR lock_end_date >= lock_start_date",
            name="lock_dates_ordered",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("ix_accounts_normalized_name", "normalized_name"),
        Index("ix_accounts_status", "status"),
    )

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240))
    account_type: Mapped[str] = mapped_column(String(24))
    opening_balance: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), default=Decimal("0"), server_default="0"
    )
    opening_balance_date: Mapped[date] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3))
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    lock_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lock_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AccountSnapshot(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "account_snapshots"
    __table_args__ = (
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_shape"),
        CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso_shape"),
        CheckConstraint(
            "fx_rate_status IN ('not_required', 'manual', 'automatic', 'missing')",
            name="fx_rate_status_allowed",
        ),
        CheckConstraint(
            "(fx_rate_status = 'missing' AND converted_balance IS NULL AND fx_rate IS NULL) OR "
            "(fx_rate_status <> 'missing' AND converted_balance IS NOT NULL AND fx_rate > 0)",
            name="conversion_complete_or_missing",
        ),
        CheckConstraint(
            "fx_rate_status <> 'not_required' OR "
            "(currency = base_currency AND fx_rate = 1 "
            "AND converted_balance = reported_balance)",
            name="same_currency_conversion_exact",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("uq_account_snapshots_account_date", "account_id", "valuation_date", unique=True),
        Index("ix_account_snapshots_account_status_date", "account_id", "status", "valuation_date"),
    )

    account_snapshot_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id", ondelete="RESTRICT"))
    valuation_date: Mapped[date] = mapped_column(Date)
    reported_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))
    converted_balance: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    fx_rate_status: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Category(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint("category_kind IN ('expense', 'income')", name="kind_allowed"),
        CheckConstraint(
            "parent_category_id IS NULL OR parent_category_id <> category_id",
            name="parent_not_self",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("ix_categories_parent_category_id", "parent_category_id"),
        Index("ix_categories_normalized_name", "normalized_name"),
        Index("ix_categories_status", "status"),
    )

    category_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240))
    category_kind: Mapped[str] = mapped_column(String(16))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    parent: Mapped[Category | None] = relationship(
        "Category", remote_side="Category.category_id", back_populates="children"
    )
    children: Mapped[list[Category]] = relationship(back_populates="parent")


class CategoryLink(TimestampMixin, Base):
    __tablename__ = "category_links"
    __table_args__ = (
        CheckConstraint("lower_category_id < higher_category_id", name="canonical_pair"),
        Index(
            "uq_category_links_pair",
            "lower_category_id",
            "higher_category_id",
            unique=True,
        ),
    )

    category_link_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    lower_category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="CASCADE")
    )
    higher_category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="CASCADE")
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Provider(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "providers"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("ix_providers_normalized_name", "normalized_name"),
        Index("ix_providers_status", "status"),
    )

    provider_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160))
    normalized_name: Mapped[str] = mapped_column(String(320))
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    aliases: Mapped[list[ProviderAlias]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class ProviderAlias(TimestampMixin, Base):
    __tablename__ = "provider_aliases"
    __table_args__ = (
        Index("uq_provider_aliases_normalized_alias", "normalized_alias", unique=True),
        Index("ix_provider_aliases_provider_id", "provider_id"),
    )

    provider_alias_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="CASCADE")
    )
    alias: Mapped[str] = mapped_column(String(200))
    normalized_alias: Mapped[str] = mapped_column(String(400))

    provider: Mapped[Provider] = relationship(back_populates="aliases")


class ProviderLink(TimestampMixin, Base):
    __tablename__ = "provider_links"
    __table_args__ = (
        CheckConstraint("lower_provider_id < higher_provider_id", name="canonical_pair"),
        Index(
            "uq_provider_links_pair",
            "lower_provider_id",
            "higher_provider_id",
            unique=True,
        ),
    )

    provider_link_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    lower_provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="CASCADE")
    )
    higher_provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="CASCADE")
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)


class Tag(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("uq_tags_normalized_name", "normalized_name", unique=True),
        Index("ix_tags_status", "status"),
    )

    tag_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(160))
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)


class SharingParty(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "sharing_parties"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("ix_sharing_parties_normalized_name", "normalized_name"),
        Index("ix_sharing_parties_status", "status"),
        Index(
            "uq_sharing_parties_active_self",
            "is_self",
            unique=True,
            postgresql_where=text("is_self AND status = 'active'"),
        ),
    )

    sharing_party_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240))
    is_self: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalysisGroup(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "analysis_groups"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("uq_analysis_groups_normalized_name", "normalized_name", unique=True),
        Index("ix_analysis_groups_status", "status"),
    )

    analysis_group_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    categories: Mapped[list[AnalysisGroupCategory]] = relationship(
        back_populates="analysis_group", cascade="all, delete-orphan"
    )
    tags: Mapped[list[AnalysisGroupTag]] = relationship(
        back_populates="analysis_group", cascade="all, delete-orphan"
    )
    accounts: Mapped[list[AnalysisGroupAccount]] = relationship(
        back_populates="analysis_group", cascade="all, delete-orphan"
    )
    providers: Mapped[list[AnalysisGroupProvider]] = relationship(
        back_populates="analysis_group", cascade="all, delete-orphan"
    )


class AnalysisGroupCategory(Base):
    __tablename__ = "analysis_group_categories"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    analysis_group_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_groups.analysis_group_id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    analysis_group: Mapped[AnalysisGroup] = relationship(back_populates="categories")


class AnalysisGroupTag(Base):
    __tablename__ = "analysis_group_tags"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    analysis_group_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_groups.analysis_group_id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.tag_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    analysis_group: Mapped[AnalysisGroup] = relationship(back_populates="tags")


class AnalysisGroupAccount(Base):
    __tablename__ = "analysis_group_accounts"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    analysis_group_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_groups.analysis_group_id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    analysis_group: Mapped[AnalysisGroup] = relationship(back_populates="accounts")


class AnalysisGroupProvider(Base):
    __tablename__ = "analysis_group_providers"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    analysis_group_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_groups.analysis_group_id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    analysis_group: Mapped[AnalysisGroup] = relationship(back_populates="providers")


class Budget(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_shape"),
        CheckConstraint(
            "period_type IN ('calendar_month', 'salary_cycle', 'calendar_year', 'custom')",
            name="period_type_allowed",
        ),
        CheckConstraint("rollover_mode IN ('reset', 'rollover')", name="rollover_allowed"),
        CheckConstraint("anchor_day BETWEEN 1 AND 28", name="anchor_day_allowed"),
        CheckConstraint("ends_on IS NULL OR ends_on >= starts_on", name="dates_ordered"),
        CheckConstraint(
            "period_type <> 'custom' OR ends_on IS NOT NULL", name="custom_requires_end"
        ),
        CheckConstraint(
            "period_type <> 'custom' OR rollover_mode = 'reset'",
            name="custom_cannot_rollover",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("uq_budgets_normalized_name", "normalized_name", unique=True),
        Index("ix_budgets_status", "status"),
        Index("ix_budgets_dates", "starts_on", "ends_on"),
    )

    budget_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analysis_group_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_groups.analysis_group_id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(240))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))
    period_type: Mapped[str] = mapped_column(String(24))
    rollover_mode: Mapped[str] = mapped_column(String(12))
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    anchor_day: Mapped[int] = mapped_column(SmallInteger, default=25, server_default="25")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis_group: Mapped[AnalysisGroup | None] = relationship()
    categories: Mapped[list[BudgetCategory]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    tags: Mapped[list[BudgetTag]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    accounts: Mapped[list[BudgetAccount]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )
    providers: Mapped[list[BudgetProvider]] = relationship(
        back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetCategory(Base):
    __tablename__ = "budget_categories"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.budget_id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)
    include_descendants: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    budget: Mapped[Budget] = relationship(back_populates="categories")


class BudgetTag(Base):
    __tablename__ = "budget_tags"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.budget_id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.tag_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    budget: Mapped[Budget] = relationship(back_populates="tags")


class BudgetAccount(Base):
    __tablename__ = "budget_accounts"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.budget_id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.account_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    budget: Mapped[Budget] = relationship(back_populates="accounts")


class BudgetProvider(Base):
    __tablename__ = "budget_providers"
    __table_args__ = (
        CheckConstraint("selection_mode IN ('include', 'exclude')", name="mode_allowed"),
    )

    budget_id: Mapped[int] = mapped_column(
        ForeignKey("budgets.budget_id", ondelete="CASCADE"), primary_key=True
    )
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="RESTRICT"), primary_key=True
    )
    selection_mode: Mapped[str] = mapped_column(String(12), primary_key=True)

    budget: Mapped[Budget] = relationship(back_populates="providers")


class Transaction(ArchiveMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_kind IN ('expense', 'income', 'transfer', 'refund', "
            "'reimbursement', 'adjustment', 'investment_trade')",
            name="kind_allowed",
        ),
        CheckConstraint("original_amount > 0", name="original_amount_positive"),
        CheckConstraint("original_currency ~ '^[A-Z]{3}$'", name="original_currency_iso_shape"),
        CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso_shape"),
        CheckConstraint(
            "fx_rate_status IN ('not_required', 'manual', 'automatic', 'missing')",
            name="fx_rate_status_allowed",
        ),
        CheckConstraint(
            "(fx_rate_status = 'missing' AND converted_amount IS NULL AND fx_rate IS NULL) OR "
            "(fx_rate_status <> 'missing' AND converted_amount > 0 AND fx_rate > 0)",
            name="conversion_complete_or_missing",
        ),
        CheckConstraint(
            "fx_rate_status <> 'not_required' OR "
            "(original_currency = base_currency AND fx_rate = 1 "
            "AND converted_amount = original_amount)",
            name="same_currency_conversion_exact",
        ),
        CheckConstraint(
            "source_type IN ('manual', 'import', 'recurring', 'system')",
            name="source_type_allowed",
        ),
        CheckConstraint(
            "(transaction_kind = 'adjustment' AND adjustment_direction IN "
            "('increase', 'decrease')) OR "
            "(transaction_kind <> 'adjustment' AND adjustment_direction IS NULL)",
            name="adjustment_direction_required",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        Index("ix_transactions_transaction_date", "transaction_date"),
        Index("ix_transactions_posting_date", "posting_date"),
        Index("ix_transactions_account_id", "account_id"),
        Index("ix_transactions_provider_id", "provider_id"),
        Index("ix_transactions_status", "status"),
        Index("ix_transactions_normalized_description", "normalized_description"),
        Index(
            "uq_transactions_adjustment_source_reference",
            "source_reference",
            unique=True,
            postgresql_where=text("transaction_kind = 'adjustment'"),
        ),
    )

    transaction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.account_id", ondelete="RESTRICT"))
    provider_id: Mapped[int | None] = mapped_column(
        ForeignKey("providers.provider_id", ondelete="RESTRICT"), nullable=True
    )
    transaction_kind: Mapped[str] = mapped_column(String(24))
    transaction_date: Mapped[date] = mapped_column(Date)
    posting_date: Mapped[date] = mapped_column(Date)
    description: Mapped[str] = mapped_column(String(240))
    normalized_description: Mapped[str] = mapped_column(String(480))
    original_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    original_currency: Mapped[str] = mapped_column(String(3))
    converted_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    base_currency: Mapped[str] = mapped_column(String(3))
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    fx_rate_status: Mapped[str] = mapped_column(String(16))
    source_type: Mapped[str] = mapped_column(String(16), default="manual", server_default="manual")
    source_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjustment_direction: Mapped[str | None] = mapped_column(String(12), nullable=True)

    splits: Mapped[list[TransactionSplit]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )


class TransactionSplit(TimestampMixin, Base):
    __tablename__ = "transaction_splits"
    __table_args__ = (
        CheckConstraint("original_amount > 0", name="original_amount_positive"),
        CheckConstraint(
            "converted_amount IS NULL OR converted_amount > 0",
            name="converted_amount_positive",
        ),
        Index("ix_transaction_splits_transaction_id", "transaction_id"),
        Index("ix_transaction_splits_category_id", "category_id"),
    )

    transaction_split_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="CASCADE")
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.category_id", ondelete="RESTRICT"), nullable=True
    )
    original_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    converted_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    is_base_cost: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    memo: Mapped[str | None] = mapped_column(String(240), nullable=True)

    transaction: Mapped[Transaction] = relationship(back_populates="splits")
    tags: Mapped[list[Tag]] = relationship(secondary="transaction_split_tags")


class TransactionSplitTag(Base):
    __tablename__ = "transaction_split_tags"
    __table_args__ = (Index("ix_transaction_split_tags_tag_id", "tag_id"),)

    transaction_split_id: Mapped[int] = mapped_column(
        ForeignKey(
            "transaction_splits.transaction_split_id",
            name="fk_split_tags_split_id_splits",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    tag_id: Mapped[int] = mapped_column(
        ForeignKey("tags.tag_id", ondelete="RESTRICT"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class TransferLink(TimestampMixin, Base):
    __tablename__ = "transfer_links"
    __table_args__ = (
        CheckConstraint(
            "outgoing_transaction_id <> incoming_transaction_id",
            name="transactions_distinct",
        ),
        CheckConstraint(
            "purpose IN ('internal', 'savings', 'investment', "
            "'credit_card_payment', 'debt_repayment')",
            name="purpose_allowed",
        ),
        Index("uq_transfer_links_outgoing", "outgoing_transaction_id", unique=True),
        Index("uq_transfer_links_incoming", "incoming_transaction_id", unique=True),
    )

    transfer_link_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    outgoing_transaction_id: Mapped[int] = mapped_column(
        ForeignKey(
            "transactions.transaction_id",
            name="fk_transfer_links_outgoing_transaction_id_transactions",
            ondelete="RESTRICT",
        )
    )
    incoming_transaction_id: Mapped[int] = mapped_column(
        ForeignKey(
            "transactions.transaction_id",
            name="fk_transfer_links_incoming_transaction_id_transactions",
            ondelete="RESTRICT",
        )
    )
    purpose: Mapped[str] = mapped_column(
        String(24), default="internal", server_default="internal"
    )

    outgoing_transaction: Mapped[Transaction] = relationship(
        foreign_keys=[outgoing_transaction_id]
    )
    incoming_transaction: Mapped[Transaction] = relationship(
        foreign_keys=[incoming_transaction_id]
    )


class RefundLink(TimestampMixin, Base):
    __tablename__ = "refund_links"
    __table_args__ = (
        Index("ix_refund_links_original_expense", "original_expense_id"),
        Index("uq_refund_links_refund_transaction", "refund_transaction_id", unique=True),
    )

    refund_link_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    original_expense_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="RESTRICT")
    )
    refund_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="RESTRICT")
    )


class ReimbursementLink(TimestampMixin, Base):
    __tablename__ = "reimbursement_links"
    __table_args__ = (
        Index("ix_reimbursement_links_original_expense", "original_expense_id"),
        Index(
            "uq_reimbursement_links_reimbursement_transaction",
            "reimbursement_transaction_id",
            unique=True,
        ),
    )

    reimbursement_link_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    original_expense_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="RESTRICT")
    )
    reimbursement_transaction_id: Mapped[int] = mapped_column(
        ForeignKey("transactions.transaction_id", ondelete="RESTRICT")
    )
