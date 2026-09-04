"""Add reusable analysis groups and filtered budgets.

Revision ID: 20260829_0008
Revises: 20260829_0007
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260829_0008"
down_revision: str | None = "20260829_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analysis_groups",
        sa.Column("analysis_group_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(240), nullable=False),
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
            "status IN ('active', 'archived')", name=op.f("ck_analysis_groups_status_allowed")
        ),
        sa.PrimaryKeyConstraint("analysis_group_id", name=op.f("pk_analysis_groups")),
    )
    op.create_index(
        "uq_analysis_groups_normalized_name", "analysis_groups", ["normalized_name"], unique=True
    )
    op.create_index("ix_analysis_groups_status", "analysis_groups", ["status"])

    op.create_table(
        "analysis_group_categories",
        sa.Column("analysis_group_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("selection_mode", sa.String(12), nullable=False),
        sa.Column("include_descendants", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('include', 'exclude')",
            name=op.f("ck_analysis_group_categories_mode_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.analysis_group_id"],
            name=op.f("fk_analysis_group_categories_analysis_group_id_analysis_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name=op.f("fk_analysis_group_categories_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "analysis_group_id",
            "category_id",
            "selection_mode",
            name=op.f("pk_analysis_group_categories"),
        ),
    )
    op.create_table(
        "analysis_group_tags",
        sa.Column("analysis_group_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("selection_mode", sa.String(12), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('include', 'exclude')",
            name=op.f("ck_analysis_group_tags_mode_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.analysis_group_id"],
            name=op.f("fk_analysis_group_tags_analysis_group_id_analysis_groups"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.tag_id"],
            name=op.f("fk_analysis_group_tags_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "analysis_group_id", "tag_id", "selection_mode", name=op.f("pk_analysis_group_tags")
        ),
    )

    op.create_table(
        "budgets",
        sa.Column("budget_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("analysis_group_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(240), nullable=False),
        sa.Column("amount", sa.Numeric(20, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("period_type", sa.String(24), nullable=False),
        sa.Column("rollover_mode", sa.String(12), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("anchor_day", sa.SmallInteger(), server_default="25", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("amount > 0", name=op.f("ck_budgets_amount_positive")),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name=op.f("ck_budgets_currency_iso_shape")),
        sa.CheckConstraint(
            "period_type IN ('calendar_month', 'salary_cycle', 'calendar_year', 'custom')",
            name=op.f("ck_budgets_period_type_allowed"),
        ),
        sa.CheckConstraint(
            "rollover_mode IN ('reset', 'rollover')", name=op.f("ck_budgets_rollover_allowed")
        ),
        sa.CheckConstraint(
            "anchor_day BETWEEN 1 AND 28", name=op.f("ck_budgets_anchor_day_allowed")
        ),
        sa.CheckConstraint(
            "ends_on IS NULL OR ends_on >= starts_on", name=op.f("ck_budgets_dates_ordered")
        ),
        sa.CheckConstraint(
            "period_type <> 'custom' OR ends_on IS NOT NULL",
            name=op.f("ck_budgets_custom_requires_end"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name=op.f("ck_budgets_status_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["analysis_group_id"],
            ["analysis_groups.analysis_group_id"],
            name=op.f("fk_budgets_analysis_group_id_analysis_groups"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("budget_id", name=op.f("pk_budgets")),
    )
    op.create_index("uq_budgets_normalized_name", "budgets", ["normalized_name"], unique=True)
    op.create_index("ix_budgets_status", "budgets", ["status"])
    op.create_index("ix_budgets_dates", "budgets", ["starts_on", "ends_on"])

    op.create_table(
        "budget_categories",
        sa.Column("budget_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.Column("selection_mode", sa.String(12), nullable=False),
        sa.Column("include_descendants", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('include', 'exclude')",
            name=op.f("ck_budget_categories_mode_allowed"),
        ),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.budget_id"],
            name=op.f("fk_budget_categories_budget_id_budgets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.category_id"],
            name=op.f("fk_budget_categories_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "budget_id", "category_id", "selection_mode", name=op.f("pk_budget_categories")
        ),
    )
    op.create_table(
        "budget_tags",
        sa.Column("budget_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.Column("selection_mode", sa.String(12), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('include', 'exclude')", name=op.f("ck_budget_tags_mode_allowed")
        ),
        sa.ForeignKeyConstraint(
            ["budget_id"],
            ["budgets.budget_id"],
            name=op.f("fk_budget_tags_budget_id_budgets"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.tag_id"],
            name=op.f("fk_budget_tags_tag_id_tags"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "budget_id", "tag_id", "selection_mode", name=op.f("pk_budget_tags")
        ),
    )


def downgrade() -> None:
    op.drop_table("budget_tags")
    op.drop_table("budget_categories")
    op.drop_index("ix_budgets_dates", table_name="budgets")
    op.drop_index("ix_budgets_status", table_name="budgets")
    op.drop_index("uq_budgets_normalized_name", table_name="budgets")
    op.drop_table("budgets")
    op.drop_table("analysis_group_tags")
    op.drop_table("analysis_group_categories")
    op.drop_index("ix_analysis_groups_status", table_name="analysis_groups")
    op.drop_index("uq_analysis_groups_normalized_name", table_name="analysis_groups")
    op.drop_table("analysis_groups")
