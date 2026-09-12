"""Add decimal fund holdings alongside stock holdings.

Revision ID: 20260912_0016
Revises: 20260912_0015
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0016"
down_revision: str | None = "20260912_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "investment_positions",
        sa.Column(
            "instrument_type",
            sa.String(length=16),
            server_default="stock",
            nullable=False,
        ),
    )
    op.drop_constraint(
        "ck_investment_positions_shares_non_negative",
        "investment_positions",
        type_="check",
    )
    op.alter_column(
        "investment_positions",
        "shares",
        existing_type=sa.BigInteger(),
        type_=sa.Numeric(24, 8),
        existing_nullable=False,
        postgresql_using="shares::numeric(24, 8)",
    )
    op.create_check_constraint(
        "ck_investment_positions_shares_non_negative",
        "investment_positions",
        "shares >= 0",
    )
    op.create_check_constraint(
        "ck_investment_positions_instrument_type_allowed",
        "investment_positions",
        "instrument_type IN ('stock', 'fund')",
    )
    op.create_check_constraint(
        "ck_investment_positions_stock_shares_whole",
        "investment_positions",
        "instrument_type = 'fund' OR shares = trunc(shares)",
    )
    op.drop_index("uq_investment_positions_user_ticker", table_name="investment_positions")
    op.create_index(
        "uq_investment_positions_user_instrument",
        "investment_positions",
        ["user_id", "instrument_type", "ticker"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_investment_positions_user_instrument",
        table_name="investment_positions",
    )
    op.execute("DELETE FROM investment_positions WHERE instrument_type = 'fund'")
    op.create_index(
        "uq_investment_positions_user_ticker",
        "investment_positions",
        ["user_id", "ticker"],
        unique=True,
    )
    op.drop_constraint(
        "ck_investment_positions_stock_shares_whole",
        "investment_positions",
        type_="check",
    )
    op.drop_constraint(
        "ck_investment_positions_instrument_type_allowed",
        "investment_positions",
        type_="check",
    )
    op.drop_constraint(
        "ck_investment_positions_shares_non_negative",
        "investment_positions",
        type_="check",
    )
    op.alter_column(
        "investment_positions",
        "shares",
        existing_type=sa.Numeric(24, 8),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="shares::bigint",
    )
    op.create_check_constraint(
        "ck_investment_positions_shares_non_negative",
        "investment_positions",
        "shares >= 0",
    )
    op.drop_column("investment_positions", "instrument_type")
