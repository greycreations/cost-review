"""Prevent rollover on a one-off custom budget interval.

Revision ID: 20260829_0009
Revises: 20260829_0008
Create Date: 2026-08-29
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260829_0009"
down_revision: str | None = "20260829_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        op.f("ck_budgets_custom_cannot_rollover"),
        "budgets",
        "period_type <> 'custom' OR rollover_mode = 'reset'",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_budgets_custom_cannot_rollover"),
        "budgets",
        type_="check",
    )
