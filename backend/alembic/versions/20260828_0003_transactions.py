"""Create transaction headers, components, tags, and balance invariants.

Revision ID: 20260828_0003
Revises: 20260828_0002
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0003"
down_revision: str | None = "20260828_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("transaction_kind", sa.String(length=24), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("posting_date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=240), nullable=False),
        sa.Column("normalized_description", sa.String(length=480), nullable=False),
        sa.Column("original_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("original_currency", sa.String(length=3), nullable=False),
        sa.Column("converted_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("base_currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate", sa.Numeric(20, 10), nullable=True),
        sa.Column("fx_rate_status", sa.String(length=16), nullable=False),
        sa.Column("source_type", sa.String(length=16), server_default="manual", nullable=False),
        sa.Column("source_reference", sa.String(length=240), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            "transaction_kind IN ('expense', 'income', 'transfer', 'refund', "
            "'reimbursement', 'adjustment', 'investment_trade')",
            name="kind_allowed",
        ),
        sa.CheckConstraint("original_amount > 0", name="original_amount_positive"),
        sa.CheckConstraint("original_currency ~ '^[A-Z]{3}$'", name="original_currency_iso_shape"),
        sa.CheckConstraint("base_currency ~ '^[A-Z]{3}$'", name="base_currency_iso_shape"),
        sa.CheckConstraint(
            "fx_rate_status IN ('not_required', 'manual', 'automatic', 'missing')",
            name="fx_rate_status_allowed",
        ),
        sa.CheckConstraint(
            "(fx_rate_status = 'missing' AND converted_amount IS NULL AND fx_rate IS NULL) OR "
            "(fx_rate_status <> 'missing' AND converted_amount > 0 AND fx_rate > 0)",
            name="conversion_complete_or_missing",
        ),
        sa.CheckConstraint(
            "fx_rate_status <> 'not_required' OR "
            "(original_currency = base_currency AND fx_rate = 1 "
            "AND converted_amount = original_amount)",
            name="same_currency_conversion_exact",
        ),
        sa.CheckConstraint(
            "source_type IN ('manual', 'import', 'recurring', 'system')",
            name="source_type_allowed",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name="fk_transactions_account_id_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            name="fk_transactions_provider_id_providers",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("transaction_id", name="pk_transactions"),
    )
    op.create_index("ix_transactions_transaction_date", "transactions", ["transaction_date"])
    op.create_index("ix_transactions_posting_date", "transactions", ["posting_date"])
    op.create_index("ix_transactions_account_id", "transactions", ["account_id"])
    op.create_index("ix_transactions_provider_id", "transactions", ["provider_id"])
    op.create_index("ix_transactions_status", "transactions", ["status"])
    op.create_index(
        "ix_transactions_normalized_description", "transactions", ["normalized_description"]
    )

    op.create_table(
        "transaction_splits",
        sa.Column(
            "transaction_split_id", sa.BigInteger(), sa.Identity(always=False), nullable=False
        ),
        sa.Column("transaction_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("original_amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("converted_amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("is_base_cost", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("memo", sa.String(length=240), nullable=True),
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
        sa.CheckConstraint("original_amount > 0", name="original_amount_positive"),
        sa.CheckConstraint(
            "converted_amount IS NULL OR converted_amount > 0",
            name="converted_amount_positive",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name="fk_transaction_splits_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.transaction_id"],
            name="fk_transaction_splits_transaction_id_transactions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("transaction_split_id", name="pk_transaction_splits"),
    )
    op.create_index(
        "ix_transaction_splits_transaction_id", "transaction_splits", ["transaction_id"]
    )
    op.create_index("ix_transaction_splits_category_id", "transaction_splits", ["category_id"])

    op.create_table(
        "transaction_split_tags",
        sa.Column("transaction_split_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.tag_id"],
            name="fk_transaction_split_tags_tag_id_tags",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_split_id"],
            ["transaction_splits.transaction_split_id"],
            name="fk_split_tags_split_id_splits",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("transaction_split_id", "tag_id", name="pk_transaction_split_tags"),
    )
    op.create_index("ix_transaction_split_tags_tag_id", "transaction_split_tags", ["tag_id"])

    op.execute(
        """
        CREATE FUNCTION cost_review_transaction_splits_balanced()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            target_id bigint;
            header_original numeric(20, 4);
            header_converted numeric(20, 4);
            split_original numeric(20, 4);
            split_converted numeric(20, 4);
            split_count integer;
            converted_count integer;
        BEGIN
            target_id := COALESCE(NEW.transaction_id, OLD.transaction_id);

            SELECT original_amount, converted_amount
            INTO header_original, header_converted
            FROM transactions
            WHERE transaction_id = target_id;

            IF NOT FOUND THEN
                RETURN NULL;
            END IF;

            SELECT
                count(*),
                COALESCE(sum(original_amount), 0),
                count(converted_amount),
                sum(converted_amount)
            INTO split_count, split_original, converted_count, split_converted
            FROM transaction_splits
            WHERE transaction_id = target_id;

            IF split_count = 0 OR split_original <> header_original THEN
                RAISE EXCEPTION 'transaction components must equal original amount'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transaction_splits_original_total';
            END IF;

            IF header_converted IS NULL THEN
                IF converted_count <> 0 THEN
                    RAISE EXCEPTION 'missing FX transaction cannot have converted components'
                        USING ERRCODE = '23514',
                              CONSTRAINT = 'ck_transaction_splits_converted_missing';
                END IF;
            ELSIF converted_count <> split_count OR split_converted <> header_converted THEN
                RAISE EXCEPTION 'transaction components must equal converted amount'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transaction_splits_converted_total';
            END IF;

            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_transaction_splits_balanced
        AFTER INSERT OR UPDATE OR DELETE ON transaction_splits
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transaction_splits_balanced()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_transaction_header_balanced
        AFTER INSERT OR UPDATE OF original_amount, converted_amount ON transactions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transaction_splits_balanced()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_transaction_header_balanced ON transactions")
    op.execute("DROP TRIGGER trg_transaction_splits_balanced ON transaction_splits")
    op.execute("DROP FUNCTION cost_review_transaction_splits_balanced()")
    op.drop_index("ix_transaction_split_tags_tag_id", table_name="transaction_split_tags")
    op.drop_table("transaction_split_tags")
    op.drop_index("ix_transaction_splits_category_id", table_name="transaction_splits")
    op.drop_index("ix_transaction_splits_transaction_id", table_name="transaction_splits")
    op.drop_table("transaction_splits")
    op.drop_index("ix_transactions_normalized_description", table_name="transactions")
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_provider_id", table_name="transactions")
    op.drop_index("ix_transactions_account_id", table_name="transactions")
    op.drop_index("ix_transactions_posting_date", table_name="transactions")
    op.drop_index("ix_transactions_transaction_date", table_name="transactions")
    op.drop_table("transactions")
