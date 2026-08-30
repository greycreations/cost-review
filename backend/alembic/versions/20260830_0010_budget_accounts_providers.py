"""Add account and provider selections to budgets and Analysis Groups.

Revision ID: 20260830_0010
Revises: 20260829_0009
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260830_0010"
down_revision: str | None = "20260829_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _selection_table(name: str, owner_table: str, owner_column: str, target: str) -> None:
    target_column = f"{target[:-1]}_id"
    op.create_table(
        name,
        sa.Column(owner_column, sa.BigInteger(), nullable=False),
        sa.Column(target_column, sa.BigInteger(), nullable=False),
        sa.Column("selection_mode", sa.String(12), nullable=False),
        sa.CheckConstraint(
            "selection_mode IN ('include', 'exclude')",
            name=op.f(f"ck_{name}_mode_allowed"),
        ),
        sa.ForeignKeyConstraint(
            [owner_column],
            [f"{owner_table}.{owner_column}"],
            name=op.f(f"fk_{name}_{owner_column}_{owner_table}"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            [target_column],
            [f"{target}.{target_column}"],
            name=op.f(f"fk_{name}_{target_column}_{target}"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            owner_column,
            target_column,
            "selection_mode",
            name=op.f(f"pk_{name}"),
        ),
    )


def upgrade() -> None:
    _selection_table("analysis_group_accounts", "analysis_groups", "analysis_group_id", "accounts")
    _selection_table(
        "analysis_group_providers", "analysis_groups", "analysis_group_id", "providers"
    )
    _selection_table("budget_accounts", "budgets", "budget_id", "accounts")
    _selection_table("budget_providers", "budgets", "budget_id", "providers")


def downgrade() -> None:
    op.drop_table("budget_providers")
    op.drop_table("budget_accounts")
    op.drop_table("analysis_group_providers")
    op.drop_table("analysis_group_accounts")
