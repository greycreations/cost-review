"""Create accounts and reusable ledger master data.

Revision ID: 20260828_0002
Revises: 20260828_0001
Create Date: 2026-08-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260828_0002"
down_revision: str | None = "20260828_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("account_type", sa.String(length=24), nullable=False),
        sa.Column("opening_balance", sa.Numeric(20, 4), server_default="0", nullable=False),
        sa.Column("opening_balance_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("interest_rate", sa.Numeric(9, 6), nullable=True),
        sa.Column("is_locked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("lock_start_date", sa.Date(), nullable=True),
        sa.Column("lock_end_date", sa.Date(), nullable=True),
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
            "account_type IN ('current', 'savings', 'credit_card', 'investment', "
            "'loan_debt', 'value_based', 'cash', 'other')",
            name="account_type_allowed",
        ),
        sa.CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_iso_shape"),
        sa.CheckConstraint(
            "interest_rate IS NULL OR interest_rate BETWEEN -100 AND 1000",
            name="interest_rate_reasonable",
        ),
        sa.CheckConstraint(
            "lock_end_date IS NULL OR lock_start_date IS NOT NULL",
            name="lock_end_requires_start",
        ),
        sa.CheckConstraint(
            "lock_end_date IS NULL OR lock_end_date >= lock_start_date",
            name="lock_dates_ordered",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.PrimaryKeyConstraint("account_id", name="pk_accounts"),
    )
    op.create_index("ix_accounts_normalized_name", "accounts", ["normalized_name"])
    op.create_index("ix_accounts_status", "accounts", ["status"])

    op.create_table(
        "categories",
        sa.Column("category_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("parent_category_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("category_kind", sa.String(length=16), nullable=False),
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
        sa.CheckConstraint("category_kind IN ('expense', 'income')", name="kind_allowed"),
        sa.CheckConstraint(
            "parent_category_id IS NULL OR parent_category_id <> category_id",
            name="parent_not_self",
        ),
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.ForeignKeyConstraint(
            ["parent_category_id"],
            ["categories.category_id"],
            name="fk_categories_parent_category_id_categories",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("category_id", name="pk_categories"),
    )
    op.create_index("ix_categories_parent_category_id", "categories", ["parent_category_id"])
    op.create_index("ix_categories_normalized_name", "categories", ["normalized_name"])
    op.create_index("ix_categories_status", "categories", ["status"])

    op.execute(
        """
        CREATE FUNCTION cost_review_category_parent_acyclic()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF NEW.parent_category_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF EXISTS (
                WITH RECURSIVE ancestors(category_id, parent_category_id) AS (
                    SELECT category_id, parent_category_id
                    FROM categories
                    WHERE category_id = NEW.parent_category_id
                    UNION
                    SELECT category.category_id, category.parent_category_id
                    FROM categories AS category
                    JOIN ancestors ON category.category_id = ancestors.parent_category_id
                )
                SELECT 1 FROM ancestors WHERE category_id = NEW.category_id
            ) THEN
                RAISE EXCEPTION 'category hierarchy cycle'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_categories_hierarchy_acyclic';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_categories_parent_acyclic
        BEFORE INSERT OR UPDATE OF parent_category_id ON categories
        FOR EACH ROW EXECUTE FUNCTION cost_review_category_parent_acyclic()
        """
    )

    op.create_table(
        "providers",
        sa.Column("provider_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("normalized_name", sa.String(length=320), nullable=False),
        sa.Column("website", sa.String(length=512), nullable=True),
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
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.PrimaryKeyConstraint("provider_id", name="pk_providers"),
    )
    op.create_index("ix_providers_normalized_name", "providers", ["normalized_name"])
    op.create_index("ix_providers_status", "providers", ["status"])

    op.create_table(
        "tags",
        sa.Column("tag_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=160), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
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
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.PrimaryKeyConstraint("tag_id", name="pk_tags"),
    )
    op.create_index("uq_tags_normalized_name", "tags", ["normalized_name"], unique=True)
    op.create_index("ix_tags_status", "tags", ["status"])

    op.create_table(
        "sharing_parties",
        sa.Column("sharing_party_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=240), nullable=False),
        sa.Column("is_self", sa.Boolean(), server_default="false", nullable=False),
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
        sa.CheckConstraint("status IN ('active', 'archived')", name="status_allowed"),
        sa.PrimaryKeyConstraint("sharing_party_id", name="pk_sharing_parties"),
    )
    op.create_index("ix_sharing_parties_normalized_name", "sharing_parties", ["normalized_name"])
    op.create_index("ix_sharing_parties_status", "sharing_parties", ["status"])
    op.create_index(
        "uq_sharing_parties_active_self",
        "sharing_parties",
        ["is_self"],
        unique=True,
        postgresql_where=sa.text("is_self AND status = 'active'"),
    )

    op.create_table(
        "category_links",
        sa.Column("category_link_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lower_category_id", sa.BigInteger(), nullable=False),
        sa.Column("higher_category_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
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
            "lower_category_id < higher_category_id",
            name="canonical_pair",
        ),
        sa.ForeignKeyConstraint(
            ["higher_category_id"],
            ["categories.category_id"],
            name="fk_category_links_higher_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lower_category_id"],
            ["categories.category_id"],
            name="fk_category_links_lower_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("category_link_id", name="pk_category_links"),
    )
    op.create_index(
        "uq_category_links_pair",
        "category_links",
        ["lower_category_id", "higher_category_id"],
        unique=True,
    )

    op.create_table(
        "provider_aliases",
        sa.Column("provider_alias_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("provider_id", sa.BigInteger(), nullable=False),
        sa.Column("alias", sa.String(length=200), nullable=False),
        sa.Column("normalized_alias", sa.String(length=400), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.provider_id"],
            name="fk_provider_aliases_provider_id_providers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("provider_alias_id", name="pk_provider_aliases"),
    )
    op.create_index("ix_provider_aliases_provider_id", "provider_aliases", ["provider_id"])
    op.create_index(
        "uq_provider_aliases_normalized_alias",
        "provider_aliases",
        ["normalized_alias"],
        unique=True,
    )

    op.create_table(
        "provider_links",
        sa.Column("provider_link_id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lower_provider_id", sa.BigInteger(), nullable=False),
        sa.Column("higher_provider_id", sa.BigInteger(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
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
            "lower_provider_id < higher_provider_id",
            name="canonical_pair",
        ),
        sa.ForeignKeyConstraint(
            ["higher_provider_id"],
            ["providers.provider_id"],
            name="fk_provider_links_higher_provider_id_providers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["lower_provider_id"],
            ["providers.provider_id"],
            name="fk_provider_links_lower_provider_id_providers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("provider_link_id", name="pk_provider_links"),
    )
    op.create_index(
        "uq_provider_links_pair",
        "provider_links",
        ["lower_provider_id", "higher_provider_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_provider_links_pair", table_name="provider_links")
    op.drop_table("provider_links")
    op.drop_index("uq_provider_aliases_normalized_alias", table_name="provider_aliases")
    op.drop_index("ix_provider_aliases_provider_id", table_name="provider_aliases")
    op.drop_table("provider_aliases")
    op.drop_index("uq_category_links_pair", table_name="category_links")
    op.drop_table("category_links")
    op.drop_index("uq_sharing_parties_active_self", table_name="sharing_parties")
    op.drop_index("ix_sharing_parties_status", table_name="sharing_parties")
    op.drop_index("ix_sharing_parties_normalized_name", table_name="sharing_parties")
    op.drop_table("sharing_parties")
    op.drop_index("ix_tags_status", table_name="tags")
    op.drop_index("uq_tags_normalized_name", table_name="tags")
    op.drop_table("tags")
    op.drop_index("ix_providers_status", table_name="providers")
    op.drop_index("ix_providers_normalized_name", table_name="providers")
    op.drop_table("providers")
    op.execute("DROP TRIGGER trg_categories_parent_acyclic ON categories")
    op.execute("DROP FUNCTION cost_review_category_parent_acyclic()")
    op.drop_index("ix_categories_status", table_name="categories")
    op.drop_index("ix_categories_normalized_name", table_name="categories")
    op.drop_index("ix_categories_parent_category_id", table_name="categories")
    op.drop_table("categories")
    op.drop_index("ix_accounts_status", table_name="accounts")
    op.drop_index("ix_accounts_normalized_name", table_name="accounts")
    op.drop_table("accounts")
