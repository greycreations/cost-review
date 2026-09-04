"""Add adjustment direction and append-only audit events.

Revision ID: 20260903_0011
Revises: 20260830_0010
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260903_0011"
down_revision: str | None = "20260830_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("adjustment_direction", sa.String(12)))
    op.create_check_constraint(
        op.f("ck_transactions_adjustment_direction_required"),
        "transactions",
        "(transaction_kind = 'adjustment' AND adjustment_direction IN "
        "('increase', 'decrease')) OR "
        "(transaction_kind <> 'adjustment' AND adjustment_direction IS NULL)",
    )
    op.create_index(
        "uq_transactions_adjustment_source_reference",
        "transactions",
        ["source_reference"],
        unique=True,
        postgresql_where=sa.text("transaction_kind = 'adjustment'"),
    )
    op.create_table(
        "audit_events",
        sa.Column("audit_event_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("change_source", sa.String(16), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "action IN ('created', 'updated', 'archived', 'restored', "
            "'balance_adjusted', 'permanently_deleted')",
            name=op.f("ck_audit_events_action_allowed"),
        ),
        sa.CheckConstraint(
            "change_source IN ('user', 'system', 'import', 'restore')",
            name=op.f("ck_audit_events_change_source_allowed"),
        ),
        sa.PrimaryKeyConstraint("audit_event_id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_entity",
        "audit_events",
        ["entity_type", "entity_id", "created_at"],
    )
    op.create_index(
        "ix_audit_events_created_at", "audit_events", ["created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index(
        "uq_transactions_adjustment_source_reference", table_name="transactions"
    )
    op.drop_constraint(
        op.f("ck_transactions_adjustment_direction_required"),
        "transactions",
        type_="check",
    )
    op.drop_column("transactions", "adjustment_direction")
