"""Constrain transfer purpose to destination account semantics.

Revision ID: 20260828_0005
Revises: 20260828_0004
Create Date: 2026-08-28
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260828_0005"
down_revision: str | None = "20260828_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION cost_review_transfer_purpose_destination_valid()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM transfer_links AS link
                JOIN transactions AS incoming
                  ON incoming.transaction_id = link.incoming_transaction_id
                JOIN accounts AS destination
                  ON destination.account_id = incoming.account_id
                WHERE (
                    link.purpose = 'investment'
                    AND destination.account_type <> 'investment'
                ) OR (
                    link.purpose = 'credit_card_payment'
                    AND destination.account_type <> 'credit_card'
                ) OR (
                    link.purpose = 'debt_repayment'
                    AND destination.account_type <> 'loan_debt'
                )
            ) THEN
                RAISE EXCEPTION 'transfer purpose does not match destination account type'
                    USING ERRCODE = '23514',
                          CONSTRAINT = 'ck_transfer_purpose_destination_type';
            END IF;
            RETURN NULL;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_transfer_links_purpose_destination_valid
        AFTER INSERT OR UPDATE OR DELETE ON transfer_links
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transfer_purpose_destination_valid()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_transactions_transfer_purpose_destination_valid
        AFTER INSERT OR UPDATE OR DELETE ON transactions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transfer_purpose_destination_valid()
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_accounts_transfer_purpose_destination_valid
        AFTER UPDATE OF account_type ON accounts
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION cost_review_transfer_purpose_destination_valid()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER trg_accounts_transfer_purpose_destination_valid ON accounts"
    )
    op.execute(
        "DROP TRIGGER trg_transactions_transfer_purpose_destination_valid ON transactions"
    )
    op.execute(
        "DROP TRIGGER trg_transfer_links_purpose_destination_valid ON transfer_links"
    )
    op.execute("DROP FUNCTION cost_review_transfer_purpose_destination_valid()")
