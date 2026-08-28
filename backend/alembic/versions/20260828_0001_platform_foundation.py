"""Create the PostgreSQL platform foundation.

Revision ID: 20260828_0001
Revises:
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "environment_metadata",
        sa.Column("metadata_id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("environment", sa.String(length=10), nullable=False),
        sa.Column("data_plane_id", sa.Uuid(), nullable=False),
        sa.Column("reset_generation", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "initialized_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("environment IN ('production', 'test')", name="environment_allowed"),
        sa.CheckConstraint("metadata_id = 1", name="singleton"),
        sa.CheckConstraint("reset_generation >= 0", name="reset_generation_non_negative"),
        sa.PrimaryKeyConstraint("metadata_id", name="pk_environment_metadata"),
        sa.UniqueConstraint("data_plane_id", name="uq_environment_metadata_data_plane_id"),
    )

    op.create_table(
        "users",
        sa.Column(
            "user_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("normalized_username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id", name="pk_users"),
    )
    op.create_index("ix_users_normalized_username", "users", ["normalized_username"], unique=True)

    op.create_table(
        "app_settings",
        sa.Column(
            "settings_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("language", sa.String(length=2), server_default="sv", nullable=False),
        sa.Column("region", sa.String(length=16), server_default="SE", nullable=False),
        sa.Column("base_currency", sa.String(length=3), server_default="SEK", nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="Europe/Stockholm",
            nullable=False,
        ),
        sa.Column(
            "date_format", sa.String(length=10), server_default="YYYY-MM-DD", nullable=False
        ),
        sa.Column(
            "number_format", sa.String(length=16), server_default="space-comma", nullable=False
        ),
        sa.Column("week_start", sa.String(length=10), server_default="monday", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso_shape"),
        sa.CheckConstraint(
            "date_format IN ('YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY')",
            name="date_format_allowed",
        ),
        sa.CheckConstraint("language IN ('sv', 'en')", name="language_allowed"),
        sa.CheckConstraint(
            "number_format IN ('space-comma', 'comma-dot', 'dot-comma')",
            name="number_format_allowed",
        ),
        sa.CheckConstraint(
            "week_start IN ('monday', 'saturday', 'sunday')", name="week_start_allowed"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.user_id"], name="fk_app_settings_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("settings_id", name="pk_app_settings"),
        sa.UniqueConstraint("user_id", name="uq_app_settings_user_id"),
    )

    op.create_table(
        "sessions",
        sa.Column("session_token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.user_id"], name="fk_sessions_user_id_users", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("session_token_hash", name="pk_sessions"),
    )
    op.create_index("ix_sessions_expires_at", "sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_sessions_expires_at", table_name="sessions")
    op.drop_table("sessions")
    op.drop_table("app_settings")
    op.drop_index("ix_users_normalized_username", table_name="users")
    op.drop_table("users")
    op.drop_table("environment_metadata")
