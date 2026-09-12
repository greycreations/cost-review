"""Add administrator roles for multi-user account management.

Revision ID: 20260912_0015
Revises: 20260911_0014
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260912_0015"
down_revision: str | None = "20260911_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute(
        "UPDATE users SET is_admin = true "
        "WHERE user_id = (SELECT MIN(user_id) FROM users)"
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
