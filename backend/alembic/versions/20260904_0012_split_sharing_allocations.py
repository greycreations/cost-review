"""Add percentage sharing allocations to transaction splits.

Revision ID: 20260904_0012
Revises: 20260903_0011
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260904_0012"
down_revision: str | None = "20260903_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transaction_split_shares",
        sa.Column("transaction_split_id", sa.BigInteger(), nullable=False),
        sa.Column("sharing_party_id", sa.BigInteger(), nullable=False),
        sa.Column("percentage", sa.Numeric(7, 4), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "percentage > 0 AND percentage <= 100",
            name=op.f("ck_transaction_split_shares_percentage_range"),
        ),
        sa.ForeignKeyConstraint(
            ["sharing_party_id"],
            ["sharing_parties.sharing_party_id"],
            name=op.f(
                "fk_transaction_split_shares_sharing_party_id_sharing_parties"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_split_id"],
            ["transaction_splits.transaction_split_id"],
            name=op.f(
                "fk_transaction_split_shares_transaction_split_id_transaction_splits"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "transaction_split_id",
            "sharing_party_id",
            name=op.f("pk_transaction_split_shares"),
        ),
    )
    op.create_index(
        "ix_transaction_split_shares_party_id",
        "transaction_split_shares",
        ["sharing_party_id"],
    )
    op.execute(
        """
        CREATE FUNCTION cost_review_split_shares_total_100()
        RETURNS trigger AS $$
        DECLARE
            affected_split_id bigint;
            allocation_total numeric(11, 4);
        BEGIN
            affected_split_id := COALESCE(NEW.transaction_split_id, OLD.transaction_split_id);
            SELECT COALESCE(SUM(percentage), 0)
              INTO allocation_total
              FROM transaction_split_shares
             WHERE transaction_split_id = affected_split_id;
            IF allocation_total <> 0 AND allocation_total <> 100 THEN
                RAISE EXCEPTION
                    'sharing allocations for transaction split % must total 100, got %',
                    affected_split_id,
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
        CREATE CONSTRAINT TRIGGER trg_transaction_split_shares_total_100
        AFTER INSERT OR UPDATE OR DELETE ON transaction_split_shares
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_split_shares_total_100();
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_transaction_split_shares_total_100 "
        "ON transaction_split_shares"
    )
    op.execute("DROP FUNCTION cost_review_split_shares_total_100()")
    op.drop_index(
        "ix_transaction_split_shares_party_id",
        table_name="transaction_split_shares",
    )
    op.drop_table("transaction_split_shares")
