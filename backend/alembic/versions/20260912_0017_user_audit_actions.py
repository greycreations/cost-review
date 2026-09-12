"""Allow audit actions emitted by user administration.

Revision ID: 20260912_0017
Revises: 20260912_0016
Create Date: 2026-09-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260912_0017"
down_revision: str | None = "20260912_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("ck_audit_events_action_allowed"),
        "audit_events",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_audit_events_action_allowed"),
        "audit_events",
        "action IN ('created', 'updated', 'archived', 'restored', "
        "'balance_adjusted', 'permanently_deleted', 'password_changed', "
        "'password_reset', 'deleted')",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_audit_events_action_allowed"),
        "audit_events",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_audit_events_action_allowed"),
        "audit_events",
        "action IN ('created', 'updated', 'archived', 'restored', "
        "'balance_adjusted', 'permanently_deleted')",
    )
