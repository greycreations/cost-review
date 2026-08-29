"""Add linked refund and reimbursement events.

Revision ID: 20260829_0007
Revises: 20260828_0006
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0007"
down_revision: str | None = "20260828_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refund_links",
        sa.Column("refund_link_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("original_expense_id", sa.BigInteger(), nullable=False),
        sa.Column("refund_transaction_id", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["original_expense_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_refund_links_original_expense_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["refund_transaction_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_refund_links_refund_transaction_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("refund_link_id", name=op.f("pk_refund_links")),
    )
    op.create_index(
        "ix_refund_links_original_expense",
        "refund_links",
        ["original_expense_id"],
    )
    op.create_index(
        "uq_refund_links_refund_transaction",
        "refund_links",
        ["refund_transaction_id"],
        unique=True,
    )
    op.create_table(
        "reimbursement_links",
        sa.Column("reimbursement_link_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("original_expense_id", sa.BigInteger(), nullable=False),
        sa.Column("reimbursement_transaction_id", sa.BigInteger(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["original_expense_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_reimbursement_links_original_expense_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reimbursement_transaction_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_reimbursement_links_reimbursement_transaction_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "reimbursement_link_id", name=op.f("pk_reimbursement_links")
        ),
    )
    op.create_index(
        "ix_reimbursement_links_original_expense",
        "reimbursement_links",
        ["original_expense_id"],
    )
    op.create_index(
        "uq_reimbursement_links_reimbursement_transaction",
        "reimbursement_links",
        ["reimbursement_transaction_id"],
        unique=True,
    )
    op.execute(_RECOVERY_FUNCTION)
    for table in ("refund_links", "reimbursement_links", "transactions", "transaction_splits"):
        op.execute(
            f"""
            CREATE CONSTRAINT TRIGGER trg_{table}_recoveries_valid
            AFTER INSERT OR UPDATE OR DELETE ON {table}
            DEFERRABLE INITIALLY DEFERRED
            FOR EACH ROW EXECUTE FUNCTION cost_review_recoveries_valid()
            """
        )


def downgrade() -> None:
    for table in ("transaction_splits", "transactions", "reimbursement_links", "refund_links"):
        op.execute(f"DROP TRIGGER trg_{table}_recoveries_valid ON {table}")
    op.execute("DROP FUNCTION cost_review_recoveries_valid()")
    op.drop_index(
        "uq_reimbursement_links_reimbursement_transaction",
        table_name="reimbursement_links",
    )
    op.drop_index(
        "ix_reimbursement_links_original_expense", table_name="reimbursement_links"
    )
    op.drop_table("reimbursement_links")
    op.drop_index("uq_refund_links_refund_transaction", table_name="refund_links")
    op.drop_index("ix_refund_links_original_expense", table_name="refund_links")
    op.drop_table("refund_links")


_RECOVERY_FUNCTION = r"""
CREATE FUNCTION cost_review_recoveries_valid()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    invalid_count integer;
BEGIN
    SELECT count(*) INTO invalid_count
    FROM (
        SELECT link.original_expense_id, link.refund_transaction_id AS recovery_id,
               'refund'::text AS expected_kind
        FROM refund_links AS link
        UNION ALL
        SELECT link.original_expense_id, link.reimbursement_transaction_id,
               'reimbursement'::text
        FROM reimbursement_links AS link
    ) AS links
    JOIN transactions AS original ON original.transaction_id = links.original_expense_id
    JOIN transactions AS recovery ON recovery.transaction_id = links.recovery_id
    WHERE original.transaction_kind <> 'expense'
       OR recovery.transaction_kind <> links.expected_kind
       OR recovery.transaction_date < original.transaction_date
       OR (recovery.status = 'active' AND original.status <> 'active')
       OR recovery.transaction_id = original.transaction_id
       OR EXISTS (
            SELECT 1 FROM transaction_splits AS split
            WHERE split.transaction_id = recovery.transaction_id
              AND (split.category_id IS NOT NULL OR split.is_base_cost)
       )
       OR EXISTS (
            SELECT 1 FROM transaction_split_tags AS split_tag
            JOIN transaction_splits AS split
              ON split.transaction_split_id = split_tag.transaction_split_id
            WHERE split.transaction_id = recovery.transaction_id
       );

    IF invalid_count > 0 THEN
        RAISE EXCEPTION 'refund or reimbursement link violates ledger semantics'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_recovery_link_semantics';
    END IF;

    IF EXISTS (
        SELECT 1 FROM transactions AS recovery
        WHERE (recovery.transaction_kind = 'refund' AND NOT EXISTS (
                  SELECT 1 FROM refund_links AS link
                  WHERE link.refund_transaction_id = recovery.transaction_id
              ))
           OR (recovery.transaction_kind = 'reimbursement' AND NOT EXISTS (
                  SELECT 1 FROM reimbursement_links AS link
                  WHERE link.reimbursement_transaction_id = recovery.transaction_id
              ))
    ) THEN
        RAISE EXCEPTION 'every refund and reimbursement must link to an expense'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_recovery_requires_link';
    END IF;

    IF EXISTS (
        SELECT 1 FROM refund_links AS refund
        JOIN reimbursement_links AS reimbursement
          ON reimbursement.reimbursement_transaction_id = refund.refund_transaction_id
    ) THEN
        RAISE EXCEPTION 'a recovery transaction cannot have two link types'
            USING ERRCODE = '23505', CONSTRAINT = 'uq_recovery_transaction_link_type';
    END IF;

    IF EXISTS (
        WITH active_recoveries AS (
            SELECT original_expense_id, refund_transaction_id AS recovery_id
            FROM refund_links
            UNION ALL
            SELECT original_expense_id, reimbursement_transaction_id
            FROM reimbursement_links
        ), grouped AS (
            SELECT original.transaction_id,
                   bool_and(
                       recovery.original_currency = original.original_currency
                   ) AS same_currency,
                   bool_and(
                       original.converted_amount IS NOT NULL
                       AND recovery.converted_amount IS NOT NULL
                       AND recovery.base_currency = original.base_currency
                   ) AS base_comparable,
                   sum(recovery.original_amount) AS recovered_original,
                   sum(recovery.converted_amount) AS recovered_converted,
                   original.original_amount,
                   original.converted_amount
            FROM active_recoveries AS link
            JOIN transactions AS original
              ON original.transaction_id = link.original_expense_id
            JOIN transactions AS recovery
              ON recovery.transaction_id = link.recovery_id
             AND recovery.status = 'active'
            GROUP BY original.transaction_id, original.original_amount,
                     original.converted_amount
        )
        SELECT 1 FROM grouped
        WHERE (base_comparable AND recovered_converted > converted_amount)
           OR (NOT base_comparable AND same_currency
               AND recovered_original > original_amount)
           OR (NOT base_comparable AND NOT same_currency)
    ) THEN
        RAISE EXCEPTION 'recoveries exceed or cannot be compared with original expense'
            USING ERRCODE = '23514', CONSTRAINT = 'ck_recovery_total_within_expense';
    END IF;
    RETURN NULL;
END;
$$
"""
