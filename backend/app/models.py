from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Uuid,
    func,
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
