from datetime import date
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession
from sqlalchemy.orm import joinedload

from app.models import (
    Account,
    AccountType,
    Transaction,
    TransactionKind,
    TransferLink,
    TransferPurpose,
)

AVAILABLE_TYPES = (AccountType.CURRENT, AccountType.CASH)
INFLOW_KINDS = (TransactionKind.INCOME, TransactionKind.REFUND, TransactionKind.REIMBURSEMENT)
CAPITAL_PURPOSES = (
    TransferPurpose.SAVINGS,
    TransferPurpose.INVESTMENT,
    TransferPurpose.DEBT_REPAYMENT,
)
RETURN_PURPOSES = {
    AccountType.SAVINGS: TransferPurpose.SAVINGS,
    AccountType.INVESTMENT: TransferPurpose.INVESTMENT,
}
ZERO = Decimal("0.0000")


def available_cash_flow(
    db: DbSession, date_from: date, date_to: date, base_currency: str
) -> dict[str, object]:
    """Summarize posted movements on current and cash accounts in the reporting currency."""
    account_types = {
        account_id: kind
        for account_id, kind in db.execute(select(Account.account_id, Account.account_type))
    }
    account_ids = {
        account_id for account_id, kind in account_types.items() if kind in AVAILABLE_TYPES
    }
    totals = dict.fromkeys(
        ("inflows", "expenses", "card_payments", "other_transfers", *CAPITAL_PURPOSES), ZERO
    )
    missing_fx_count = 0
    statement = (
        select(Transaction, TransferLink)
        .outerjoin(
            TransferLink,
            or_(
                TransferLink.outgoing_transaction_id == Transaction.transaction_id,
                TransferLink.incoming_transaction_id == Transaction.transaction_id,
            ),
        )
        .options(
            joinedload(TransferLink.outgoing_transaction),
            joinedload(TransferLink.incoming_transaction),
        )
        .where(
            Transaction.account_id.in_(account_ids),
            Transaction.status == "active",
            Transaction.posting_date.between(date_from, date_to),
            Transaction.transaction_kind.in_((*INFLOW_KINDS, "expense", "transfer")),
        )
    )
    for transaction, link in db.execute(statement):
        amount = transaction.converted_amount
        if amount is None or transaction.base_currency != base_currency:
            missing_fx_count += 1
            continue

        if link is not None:
            outgoing = transaction.transaction_id == link.outgoing_transaction_id
            other = link.incoming_transaction if outgoing else link.outgoing_transaction
            bucket = "other_transfers"
            if other.account_id not in account_ids:
                if link.purpose in CAPITAL_PURPOSES:
                    bucket = link.purpose
                elif link.purpose == TransferPurpose.CREDIT_CARD_PAYMENT:
                    bucket = "card_payments"
                elif not outgoing and link.purpose == TransferPurpose.INTERNAL:
                    bucket = RETURN_PURPOSES.get(account_types[other.account_id], bucket)
            totals[bucket] += -amount if outgoing else amount
        elif transaction.transaction_kind == TransactionKind.EXPENSE:
            totals["expenses"] -= amount
        elif transaction.transaction_kind in INFLOW_KINDS:
            totals["inflows"] += amount

    return {
        "date_from": date_from,
        "date_to": date_to,
        "base_currency": base_currency,
        "account_count": len(account_ids),
        "missing_fx_count": missing_fx_count,
        "net_movement": sum(totals.values(), ZERO),
        **totals,
    }
