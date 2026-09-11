"""Add isolated investment portfolio planning state.

Revision ID: 20260911_0013
Revises: 20260904_0012
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260911_0013"
down_revision: str | None = "20260904_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investment_portfolio_settings",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "purchase_budget",
            sa.Numeric(20, 4),
            server_default="0",
            nullable=False,
        ),
        sa.Column("currency", sa.String(length=3), server_default="SEK", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purchase_budget >= 0",
            name=op.f("ck_investment_portfolio_settings_purchase_budget_non_negative"),
        ),
        sa.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name=op.f("ck_investment_portfolio_settings_currency_iso_shape"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_investment_portfolio_settings_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_investment_portfolio_settings")),
    )
    op.create_table(
        "investment_positions",
        sa.Column("investment_position_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ticker", sa.String(length=16), nullable=False),
        sa.Column("shares", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "target_percentage",
            sa.Numeric(7, 4),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "shares >= 0",
            name=op.f("ck_investment_positions_shares_non_negative"),
        ),
        sa.CheckConstraint(
            "target_percentage >= 0 AND target_percentage <= 100",
            name=op.f("ck_investment_positions_target_percentage_range"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_investment_positions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "investment_position_id",
            name=op.f("pk_investment_positions"),
        ),
    )
    op.create_index(
        "ix_investment_positions_user_id",
        "investment_positions",
        ["user_id"],
    )
    op.create_index(
        "uq_investment_positions_user_ticker",
        "investment_positions",
        ["user_id", "ticker"],
        unique=True,
    )
    op.execute(
        """
        CREATE FUNCTION cost_review_investment_allocations_max_100()
        RETURNS trigger AS $$
        DECLARE
            affected_user_id bigint;
            allocation_total numeric(11, 4);
        BEGIN
            affected_user_id := COALESCE(NEW.user_id, OLD.user_id);
            SELECT COALESCE(SUM(target_percentage), 0)
              INTO allocation_total
              FROM investment_positions
             WHERE user_id = affected_user_id;
            IF allocation_total > 100 THEN
                RAISE EXCEPTION
                    'investment allocation for user % exceeds 100: %',
                    affected_user_id,
                    allocation_total
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_investment_allocations_max_100
        AFTER INSERT OR UPDATE OR DELETE ON investment_positions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_investment_allocations_max_100();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_investment_allocations_max_100 ON investment_positions")
    op.execute("DROP FUNCTION cost_review_investment_allocations_max_100()")
    op.drop_index(
        "uq_investment_positions_user_ticker",
        table_name="investment_positions",
    )
    op.drop_index("ix_investment_positions_user_id", table_name="investment_positions")
    op.drop_table("investment_positions")
    op.drop_table("investment_portfolio_settings")
