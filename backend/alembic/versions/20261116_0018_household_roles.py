"""Introduce household roles, personal sharing parties and attributed audit events.

Every user of a data plane shares one household ledger. Access is governed by a
role (owner, member, viewer) instead of a single administrator flag. The former
global ``is_self`` sharing party becomes a party linked to the oldest owner, so
"My Share" is personal for every household member. Audit events gain the acting
user, and failed sign-ins are tracked for account lockout.

Revision ID: 20261116_0018
Revises: 20260912_0017
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261116_0018"
down_revision: str | None = "20260912_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
    )
    op.execute("UPDATE users SET role = CASE WHEN is_admin THEN 'owner' ELSE 'member' END")
    op.execute(
        "UPDATE users SET role = 'owner' "
        "WHERE NOT EXISTS (SELECT 1 FROM users WHERE role = 'owner') "
        "AND user_id = (SELECT MIN(user_id) FROM users)"
    )
    op.drop_column("users", "is_admin")
    op.create_check_constraint(
        op.f("ck_users_role_allowed"), "users", "role IN ('owner', 'member', 'viewer')"
    )
    op.add_column(
        "users",
        sa.Column("failed_login_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_check_constraint(
        op.f("ck_users_failed_login_count_non_negative"), "users", "failed_login_count >= 0"
    )

    op.add_column(
        "sharing_parties", sa.Column("user_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_sharing_parties_user_id_users"),
        "sharing_parties",
        "users",
        ["user_id"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.execute(
        "UPDATE sharing_parties SET user_id = "
        "(SELECT MIN(user_id) FROM users WHERE role = 'owner') "
        "WHERE sharing_party_id = ("
        "  SELECT MIN(sharing_party_id) FROM sharing_parties "
        "  WHERE is_self AND status = 'active'"
        ")"
    )
    op.drop_index("uq_sharing_parties_active_self", table_name="sharing_parties")
    op.drop_column("sharing_parties", "is_self")
    op.create_index(
        "uq_sharing_parties_active_user",
        "sharing_parties",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL AND status = 'active'"),
    )

    op.add_column(
        "audit_events", sa.Column("actor_user_id", sa.BigInteger(), nullable=True)
    )
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_actor_user_id", table_name="audit_events")
    op.drop_column("audit_events", "actor_user_id")

    op.drop_index("uq_sharing_parties_active_user", table_name="sharing_parties")
    op.add_column(
        "sharing_parties",
        sa.Column("is_self", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute(
        "UPDATE sharing_parties SET is_self = true "
        "WHERE sharing_party_id = ("
        "  SELECT MIN(sharing_party_id) FROM sharing_parties "
        "  WHERE user_id IS NOT NULL AND status = 'active'"
        ")"
    )
    op.create_index(
        "uq_sharing_parties_active_self",
        "sharing_parties",
        ["is_self"],
        unique=True,
        postgresql_where=sa.text("is_self AND status = 'active'"),
    )
    op.drop_constraint(
        op.f("fk_sharing_parties_user_id_users"), "sharing_parties", type_="foreignkey"
    )
    op.drop_column("sharing_parties", "user_id")

    op.drop_constraint(
        op.f("ck_users_failed_login_count_non_negative"), "users", type_="check"
    )
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_count")
    op.drop_constraint(op.f("ck_users_role_allowed"), "users", type_="check")
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.execute("UPDATE users SET is_admin = (role = 'owner')")
    op.drop_column("users", "role")
