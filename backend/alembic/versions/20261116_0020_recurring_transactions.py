"""Add recurring definitions, amount versions and occurrence decisions.

Expected occurrences are derived from definitions and are never stored as
Ledger transactions. Only a confirmation creates or links an Actual event.

Revision ID: 20261116_0020
Revises: 20261116_0019
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261116_0020"
down_revision: str | None = "20261116_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "recurring_definitions",
        sa.Column(
            "recurring_definition_id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("transaction_kind", sa.String(length=16), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("frequency", sa.String(length=16), nullable=False),
        sa.Column("interval_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "tolerance_percent", sa.Numeric(7, 4), server_default="10", nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name=op.f("ck_recurring_definitions_status_allowed"),
        ),
        sa.CheckConstraint(
            "transaction_kind IN ('expense', 'income')",
            name=op.f("ck_recurring_definitions_transaction_kind_allowed"),
        ),
        sa.CheckConstraint(
            "frequency IN ('weekly', 'monthly', 'quarterly', 'yearly')",
            name=op.f("ck_recurring_definitions_frequency_allowed"),
        ),
        sa.CheckConstraint(
            "interval_count BETWEEN 1 AND 52",
            name=op.f("ck_recurring_definitions_interval_count_range"),
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name=op.f("ck_recurring_definitions_end_after_start"),
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name=op.f("ck_recurring_definitions_currency_iso_shape"),
        ),
        sa.CheckConstraint(
            "tolerance_percent >= 0 AND tolerance_percent <= 100",
            name=op.f("ck_recurring_definitions_tolerance_range"),
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name=op.f("fk_recurring_definitions_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            name=op.f("fk_recurring_definitions_provider_id_providers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name=op.f("fk_recurring_definitions_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "recurring_definition_id", name=op.f("pk_recurring_definitions")
        ),
    )

    op.create_table(
        "recurring_versions",
        sa.Column("recurring_version_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("recurring_definition_id", sa.BigInteger(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("amount_type", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name=op.f("ck_recurring_versions_amount_positive")),
        sa.CheckConstraint(
            "amount_type IN ('fixed', 'variable')",
            name=op.f("ck_recurring_versions_amount_type_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["recurring_definition_id"],
            ["recurring_definitions.recurring_definition_id"],
            name=op.f("fk_recurring_versions_recurring_definition_id_recurring_definitions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("recurring_version_id", name=op.f("pk_recurring_versions")),
    )
    op.create_index(
        "uq_recurring_versions_effective",
        "recurring_versions",
        ["recurring_definition_id", "effective_from"],
        unique=True,
    )

    op.create_table(
        "recurring_occurrences",
        sa.Column(
            "recurring_occurrence_id", sa.BigInteger(), autoincrement=True, nullable=False
        ),
        sa.Column("recurring_definition_id", sa.BigInteger(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("expected_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("deviation_percent", sa.Numeric(9, 4), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('confirmed', 'skipped')",
            name=op.f("ck_recurring_occurrences_status_allowed"),
        ),
        sa.CheckConstraint(
            "(status = 'confirmed' AND transaction_id IS NOT NULL) OR "
            "(status = 'skipped' AND transaction_id IS NULL)",
            name=op.f("ck_recurring_occurrences_confirmed_has_transaction"),
        ),
        sa.ForeignKeyConstraint(
            ["recurring_definition_id"],
            ["recurring_definitions.recurring_definition_id"],
            name=op.f(
                "fk_recurring_occurrences_recurring_definition_id_recurring_definitions"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_recurring_occurrences_transaction_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "recurring_occurrence_id", name=op.f("pk_recurring_occurrences")
        ),
    )
    op.create_index(
        "uq_recurring_occurrences_due",
        "recurring_occurrences",
        ["recurring_definition_id", "due_date"],
        unique=True,
    )
    op.create_index(
        "uq_recurring_occurrences_transaction",
        "recurring_occurrences",
        ["transaction_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("recurring_occurrences")
    op.drop_table("recurring_versions")
    op.drop_table("recurring_definitions")
