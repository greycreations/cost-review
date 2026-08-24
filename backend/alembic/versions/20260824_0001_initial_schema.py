"""Create provider, category, and expense tables.

Revision ID: 20260824_0001
Revises:
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260824_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "providers",
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="provider_status",
                native_enum=False,
                create_constraint=False,
                length=8,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="provider_status_allowed",
        ),
        sa.PrimaryKeyConstraint("provider_id"),
    )
    op.create_index("ix_providers_name", "providers", ["name"])

    op.create_table(
        "categories",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "archived",
                name="category_status",
                native_enum=False,
                create_constraint=False,
                length=8,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("sort_order >= 0", name="sort_order_non_negative"),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="category_status_allowed",
        ),
        sa.PrimaryKeyConstraint("category_id"),
    )
    op.create_index("ix_categories_name", "categories", ["name"])

    op.create_table(
        "expenses",
        sa.Column("expense_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default="SEK", nullable=False),
        sa.Column(
            "amount_type",
            sa.Enum(
                "exact",
                "estimated",
                name="amount_type",
                native_enum=False,
                create_constraint=False,
                length=9,
            ),
            server_default="exact",
            nullable=False,
        ),
        sa.Column(
            "recurrence_unit",
            sa.Enum(
                "day",
                "week",
                "month",
                "year",
                name="recurrence_unit",
                native_enum=False,
                create_constraint=False,
                length=5,
            ),
            nullable=True,
        ),
        sa.Column("recurrence_interval", sa.Integer(), nullable=True),
        sa.Column(
            "expense_type",
            sa.Enum(
                "recurring",
                "one_time",
                name="expense_type",
                native_enum=False,
                create_constraint=False,
                length=9,
            ),
            server_default="recurring",
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("next_payment_date", sa.Date(), nullable=True),
        sa.Column(
            "payment_method",
            sa.Enum(
                "invoice",
                "direct_debit",
                "credit_card",
                "bank_transfer",
                "other",
                name="payment_method",
                native_enum=False,
                create_constraint=False,
                length=13,
            ),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "paused",
                "ended",
                name="expense_status",
                native_enum=False,
                create_constraint=False,
                length=6,
            ),
            server_default="active",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("amount >= 0", name="amount_non_negative"),
        sa.CheckConstraint(
            "amount_type IN ('exact', 'estimated')",
            name="amount_type_allowed",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="date_order",
        ),
        sa.CheckConstraint(
            "(expense_type = 'one_time' AND recurrence_unit IS NULL "
            "AND recurrence_interval IS NULL) OR "
            "(expense_type = 'recurring' AND recurrence_unit IS NOT NULL "
            "AND recurrence_interval > 0)",
            name="recurrence_shape",
        ),
        sa.CheckConstraint(
            "recurrence_unit IS NULL OR recurrence_unit IN ('day', 'week', 'month', 'year')",
            name="recurrence_unit_allowed",
        ),
        sa.CheckConstraint(
            "expense_type IN ('recurring', 'one_time')",
            name="expense_type_allowed",
        ),
        sa.CheckConstraint(
            "payment_method IS NULL OR payment_method IN "
            "('invoice', 'direct_debit', 'credit_card', 'bank_transfer', 'other')",
            name="payment_method_allowed",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'paused', 'ended')",
            name="expense_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("expense_id"),
    )
    op.create_index("ix_expenses_category_id", "expenses", ["category_id"])
    op.create_index("ix_expenses_name", "expenses", ["name"])
    op.create_index("ix_expenses_provider_id", "expenses", ["provider_id"])
    op.create_index("ix_expenses_status", "expenses", ["status"])


def downgrade() -> None:
    op.drop_index("ix_expenses_status", table_name="expenses")
    op.drop_index("ix_expenses_provider_id", table_name="expenses")
    op.drop_index("ix_expenses_name", table_name="expenses")
    op.drop_index("ix_expenses_category_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_providers_name", table_name="providers")
    op.drop_table("providers")
