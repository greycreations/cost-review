"""Add CSV/XLSX import profiles, batches and staged rows.

Imported rows are staged and reviewed before any Ledger transaction exists.
Committed rows link one-to-one to the transaction they created, so a batch can
be undone by archiving exactly those transactions.

Revision ID: 20261116_0019
Revises: 20261116_0018
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261116_0019"
down_revision: str | None = "20261116_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_ACTIONS_BEFORE = (
    "action IN ('created', 'updated', 'archived', 'restored', "
    "'balance_adjusted', 'permanently_deleted', 'password_changed', "
    "'password_reset', 'deleted')"
)
AUDIT_ACTIONS_AFTER = (
    "action IN ('created', 'updated', 'archived', 'restored', "
    "'balance_adjusted', 'permanently_deleted', 'password_changed', "
    "'password_reset', 'deleted', 'imported', 'import_undone')"
)


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
        "import_profiles",
        sa.Column("import_profile_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("delimiter", sa.String(length=1), nullable=True),
        sa.Column("header_row", sa.Integer(), server_default="1", nullable=False),
        sa.Column("date_column", sa.String(length=120), nullable=False),
        sa.Column("description_column", sa.String(length=120), nullable=False),
        sa.Column("amount_column", sa.String(length=120), nullable=True),
        sa.Column("debit_column", sa.String(length=120), nullable=True),
        sa.Column("credit_column", sa.String(length=120), nullable=True),
        sa.Column("posting_date_column", sa.String(length=120), nullable=True),
        sa.Column("currency_column", sa.String(length=120), nullable=True),
        sa.Column("reference_column", sa.String(length=120), nullable=True),
        sa.Column("date_format", sa.String(length=32), nullable=False),
        sa.Column("decimal_separator", sa.String(length=1), nullable=False),
        sa.Column("amount_sign", sa.String(length=10), nullable=False),
        sa.Column("default_account_id", sa.BigInteger(), nullable=True),
        sa.Column("header_signature", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name=op.f("ck_import_profiles_status_allowed")
        ),
        sa.CheckConstraint(
            "decimal_separator IN (',', '.')",
            name=op.f("ck_import_profiles_decimal_separator_allowed"),
        ),
        sa.CheckConstraint(
            "amount_sign IN ('as_is', 'inverted')",
            name=op.f("ck_import_profiles_amount_sign_allowed"),
        ),
        sa.CheckConstraint(
            "header_row >= 1", name=op.f("ck_import_profiles_header_row_positive")
        ),
        sa.CheckConstraint(
            "amount_column IS NOT NULL OR debit_column IS NOT NULL "
            "OR credit_column IS NOT NULL",
            name=op.f("ck_import_profiles_amount_source_required"),
        ),
        sa.ForeignKeyConstraint(
            ["default_account_id"],
            ["accounts.account_id"],
            name=op.f("fk_import_profiles_default_account_id_accounts"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("import_profile_id", name=op.f("pk_import_profiles")),
    )
    op.create_index(
        "ix_import_profiles_normalized_name", "import_profiles", ["normalized_name"]
    )

    op.create_table(
        "import_batches",
        sa.Column("import_batch_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("import_profile_id", sa.BigInteger(), nullable=True),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="staged", nullable=False),
        sa.Column("row_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("mapping", sa.JSON(), nullable=False),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('staged', 'committed', 'undone')",
            name=op.f("ck_import_batches_status_allowed"),
        ),
        sa.CheckConstraint(
            "row_count >= 0", name=op.f("ck_import_batches_row_count_non_negative")
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.account_id"],
            name=op.f("fk_import_batches_account_id_accounts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["import_profile_id"],
            ["import_profiles.import_profile_id"],
            name=op.f("fk_import_batches_import_profile_id_import_profiles"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("import_batch_id", name=op.f("pk_import_batches")),
    )
    op.create_index("ix_import_batches_created_at", "import_batches", ["created_at"])
    op.create_index("ix_import_batches_file_sha256", "import_batches", ["file_sha256"])

    op.create_table(
        "import_rows",
        sa.Column("import_row_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("import_batch_id", sa.BigInteger(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("posting_date", sa.Date(), nullable=True),
        sa.Column("description", sa.String(length=240), nullable=True),
        sa.Column("amount", sa.Numeric(20, 4), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("reference", sa.String(length=240), nullable=True),
        sa.Column("category_id", sa.BigInteger(), nullable=True),
        sa.Column("provider_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("errors", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("duplicate_transaction_id", sa.BigInteger(), nullable=True),
        sa.Column("duplicate_confidence", sa.Integer(), nullable=True),
        sa.Column("duplicate_reason", sa.String(length=32), nullable=True),
        sa.Column("transaction_id", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('ready', 'duplicate', 'invalid', 'skipped', 'committed')",
            name=op.f("ck_import_rows_status_allowed"),
        ),
        sa.CheckConstraint(
            "duplicate_confidence IS NULL OR duplicate_confidence BETWEEN 0 AND 100",
            name=op.f("ck_import_rows_duplicate_confidence_range"),
        ),
        sa.CheckConstraint(
            "status <> 'committed' OR transaction_id IS NOT NULL",
            name=op.f("ck_import_rows_committed_row_has_transaction"),
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.import_batch_id"],
            name=op.f("fk_import_rows_import_batch_id_import_batches"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name=op.f("fk_import_rows_category_id_categories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            name=op.f("fk_import_rows_provider_id_providers"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_transaction_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_import_rows_duplicate_transaction_id_transactions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.transaction_id"],
            name=op.f("fk_import_rows_transaction_id_transactions"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("import_row_id", name=op.f("pk_import_rows")),
    )
    op.create_index(
        "ix_import_rows_batch", "import_rows", ["import_batch_id", "row_number"], unique=True
    )
    op.create_index("ix_import_rows_fingerprint", "import_rows", ["fingerprint"])
    op.create_index("uq_import_rows_transaction", "import_rows", ["transaction_id"], unique=True)

    op.drop_constraint(op.f("ck_audit_events_action_allowed"), "audit_events", type_="check")
    op.create_check_constraint(
        op.f("ck_audit_events_action_allowed"), "audit_events", AUDIT_ACTIONS_AFTER
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_audit_events_action_allowed"), "audit_events", type_="check")
    op.create_check_constraint(
        op.f("ck_audit_events_action_allowed"), "audit_events", AUDIT_ACTIONS_BEFORE
    )
    op.drop_table("import_rows")
    op.drop_table("import_batches")
    op.drop_index("ix_import_profiles_normalized_name", table_name="import_profiles")
    op.drop_table("import_profiles")
