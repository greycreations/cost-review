"""Create atomic internal-transfer links and ledger invariants.

Revision ID: 20260828_0004
Revises: 20260828_0003
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0004"
down_revision: str | None = "20260828_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transfer_links",
        sa.Column(
            "transfer_link_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("outgoing_transaction_id", sa.BigInteger(), nullable=False),
        sa.Column("incoming_transaction_id", sa.BigInteger(), nullable=False),
        sa.Column("purpose", sa.String(length=24), server_default="internal", nullable=False),
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
        sa.CheckConstraint(
            "outgoing_transaction_id <> incoming_transaction_id",
            name="transactions_distinct",
        ),
        sa.CheckConstraint(
            "purpose IN ('internal', 'savings', 'investment', "
            "'credit_card_payment', 'debt_repayment')",
            name="purpose_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["outgoing_transaction_id"],
            ["transactions.transaction_id"],
            name="fk_transfer_links_outgoing_transaction_id_transactions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incoming_transaction_id"],
            ["transactions.transaction_id"],
            name="fk_transfer_links_incoming_transaction_id_transactions",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("transfer_link_id", name="pk_transfer_links"),
    )
    op.create_index(
        "uq_transfer_links_outgoing",
        "transfer_links",
        ["outgoing_transaction_id"],
        unique=True,
    )
    op.create_index(
        "uq_transfer_links_incoming",
        "transfer_links",
        ["incoming_transaction_id"],
        unique=True,
    )

    op.execute(
        """
        CREATE FUNCTION cost_review_transfer_links_valid()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM transactions AS transaction
                WHERE transaction.transaction_kind = 'transfer'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM transfer_links AS link
                    WHERE link.outgoing_transaction_id = transaction.transaction_id
                       OR link.incoming_transaction_id = transaction.transaction_id
                  )
            ) THEN
                RAISE EXCEPTION 'every transfer transaction must belong to a transfer link'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_transaction_linked';
            END IF;

            IF EXISTS (
                SELECT transaction_id
                FROM (
                    SELECT outgoing_transaction_id AS transaction_id FROM transfer_links
                    UNION ALL
                    SELECT incoming_transaction_id AS transaction_id FROM transfer_links
                ) AS linked_transactions
                GROUP BY transaction_id
                HAVING count(*) <> 1
            ) THEN
                RAISE EXCEPTION 'a transfer transaction must have exactly one link role'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_transaction_single_role';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM transfer_links AS link
                JOIN transactions AS outgoing
                  ON outgoing.transaction_id = link.outgoing_transaction_id
                JOIN transactions AS incoming
                  ON incoming.transaction_id = link.incoming_transaction_id
                JOIN accounts AS outgoing_account
                  ON outgoing_account.account_id = outgoing.account_id
                JOIN accounts AS incoming_account
                  ON incoming_account.account_id = incoming.account_id
                WHERE outgoing.transaction_kind <> 'transfer'
                   OR incoming.transaction_kind <> 'transfer'
                   OR outgoing.account_id = incoming.account_id
                   OR outgoing.provider_id IS NOT NULL
                   OR incoming.provider_id IS NOT NULL
                   OR outgoing.source_type IS DISTINCT FROM incoming.source_type
                   OR outgoing.transaction_date IS DISTINCT FROM incoming.transaction_date
                   OR outgoing.description IS DISTINCT FROM incoming.description
                   OR outgoing.base_currency IS DISTINCT FROM incoming.base_currency
                   OR outgoing.status IS DISTINCT FROM incoming.status
                   OR outgoing.original_currency IS DISTINCT FROM outgoing_account.currency
                   OR incoming.original_currency IS DISTINCT FROM incoming_account.currency
                   OR (
                        outgoing.original_currency = incoming.original_currency
                        AND outgoing.original_amount IS DISTINCT FROM incoming.original_amount
                   )
                   OR (
                        outgoing.converted_amount IS NOT NULL
                        AND incoming.converted_amount IS NOT NULL
                        AND outgoing.converted_amount IS DISTINCT FROM incoming.converted_amount
                   )
            ) THEN
                RAISE EXCEPTION 'transfer link legs violate ledger semantics'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_link_semantics';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM transactions AS transaction
                WHERE transaction.transaction_kind = 'transfer'
                  AND (
                    SELECT count(*)
                    FROM transaction_splits AS split
                    WHERE split.transaction_id = transaction.transaction_id
                  ) <> 1
            ) THEN
                RAISE EXCEPTION 'each transfer leg must have exactly one neutral component'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_single_component';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM transaction_splits AS split
                JOIN transactions AS transaction
                  ON transaction.transaction_id = split.transaction_id
                WHERE transaction.transaction_kind = 'transfer'
                  AND (split.category_id IS NOT NULL OR split.is_base_cost)
            ) THEN
                RAISE EXCEPTION 'transfer components cannot be consumption classifications'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_component_neutral';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM transaction_split_tags AS split_tag
                JOIN transaction_splits AS split
                  ON split.transaction_split_id = split_tag.transaction_split_id
                JOIN transactions AS transaction
                  ON transaction.transaction_id = split.transaction_id
                WHERE transaction.transaction_kind = 'transfer'
            ) THEN
                RAISE EXCEPTION 'transfer components cannot carry transaction tags'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_component_untagged';
            END IF;

            RETURN NULL;
        END;
        $$
        """
    )
    for table_name in (
        "transfer_links",
        "transactions",
        "transaction_splits",
        "transaction_split_tags",
    ):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table_name}_transfer_valid
            AFTER INSERT OR UPDATE OR DELETE ON {table_name}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION cost_review_transfer_links_valid()
            """
        )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_accounts_transfer_currency_valid
        AFTER UPDATE OF currency ON accounts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transfer_links_valid()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_accounts_transfer_currency_valid ON accounts")
    for table_name in (
        "transaction_split_tags",
        "transaction_splits",
        "transactions",
        "transfer_links",
    ):
        op.execute(f"DROP TRIGGER trg_{table_name}_transfer_valid ON {table_name}")
    op.execute("DROP FUNCTION cost_review_transfer_links_valid()")
    op.drop_index("uq_transfer_links_incoming", table_name="transfer_links")
    op.drop_index("uq_transfer_links_outgoing", table_name="transfer_links")
    op.drop_table("transfer_links")
