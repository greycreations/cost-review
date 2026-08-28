from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
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
