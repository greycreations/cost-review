"""Add dated account balance and valuation snapshots.

Revision ID: 20260828_0006
Revises: 20260828_0005
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0006"
down_revision: str | None = "20260828_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_snapshots",
        sa.Column("account_snapshot_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("valuation_date", sa.Date(), nullable=False),
        sa.Column("reported_balance", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("converted_balance", sa.Numeric(20, 4), nullable=True),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("fx_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("fx_rate_status", sa.String(16), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'", name=op.f("ck_account_snapshots_currency_iso_shape")
        ),
        sa.CheckConstraint(
            "base_currency ~ '^[A-Z]{3}$'",
            name=op.f("ck_account_snapshots_base_currency_iso_shape"),
        ),
        sa.CheckConstraint(
            "fx_rate_status IN ('not_required', 'manual', 'automatic', 'missing')",
            name=op.f("ck_account_snapshots_fx_rate_status_allowed"),
        ),
        sa.CheckConstraint(
            "(fx_rate_status = 'missing' AND converted_balance IS NULL "
            "AND fx_rate IS NULL) OR (fx_rate_status <> 'missing' "
            "AND converted_balance IS NOT NULL AND fx_rate > 0)",
            name=op.f("ck_account_snapshots_conversion_complete_or_missing"),
        ),
        sa.CheckConstraint(
            "fx_rate_status <> 'not_required' OR "
            "(currency = base_currency AND fx_rate = 1 "
            "AND converted_balance = reported_balance)",
            name=op.f("ck_account_snapshots_same_currency_conversion_exact"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name=op.f("ck_account_snapshots_status_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name=op.f("fk_account_snapshots_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("account_snapshot_id", name=op.f("pk_account_snapshots")),
    )
    op.create_index(
        "uq_account_snapshots_account_date",
        "account_snapshots",
        ["account_id", "valuation_date"],
        unique=True,
    )
    op.create_index(
        "ix_account_snapshots_account_status_date",
        "account_snapshots",
        ["account_id", "status", "valuation_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_snapshots_account_status_date", table_name="account_snapshots")
    op.drop_index("uq_account_snapshots_account_date", table_name="account_snapshots")
    op.drop_table("account_snapshots")
