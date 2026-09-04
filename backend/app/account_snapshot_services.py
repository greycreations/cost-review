from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.ledger_schemas import AccountSnapshotCreate, AccountSnapshotUpdate
from app.ledger_services import _commit, _reject_nulls
from app.models import Account, AccountSnapshot, Transaction, TransferLink
from app.transaction_services import MONEY_QUANTUM, RATE_QUANTUM


def list_account_snapshots(
    db: DbSession, account: Account, *, include_archived: bool
) -> list[dict[str, object]]:
    statement = select(AccountSnapshot).where(AccountSnapshot.account_id == account.account_id)
    if not include_archived:
        statement = statement.where(AccountSnapshot.status == "active")
    models = db.scalars(
        statement.order_by(
            AccountSnapshot.valuation_date.desc(), AccountSnapshot.account_snapshot_id.desc()
        )
    )
    return [snapshot_values(db, account, model) for model in models]


def create_account_snapshot(
    db: DbSession,
    account: Account,
    payload: AccountSnapshotCreate,
    base_currency: str,
) -> dict[str, object]:
    if account.status != "active":
        raise ApiError(
            409, "archived_dependency", "Account is archived and cannot receive snapshots."
        )
    _validate_snapshot_date(account, payload.valuation_date)
    amount = payload.reported_balance.quantize(MONEY_QUANTUM)
    converted, rate, status = _resolve_snapshot_conversion(
        amount, account.currency, base_currency, payload.converted_balance, payload.fx_rate
    )
    model = AccountSnapshot(
        account_id=account.account_id,
        valuation_date=payload.valuation_date,
        reported_balance=amount,
        currency=account.currency,
        converted_balance=converted,
        base_currency=base_currency,
        fx_rate=rate,
        fx_rate_status=status,
        notes=payload.notes,
    )
    db.add(model)
    _commit(db, "account_snapshot_date_exists")
    db.refresh(model)
    return snapshot_values(db, account, model)


def update_account_snapshot(
    db: DbSession,
    account: Account,
    model: AccountSnapshot,
    payload: AccountSnapshotUpdate,
) -> dict[str, object]:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(values, {"valuation_date", "reported_balance"})
    _validate_snapshot_date(account, values.get("valuation_date", model.valuation_date))
    amount = values.get("reported_balance", model.reported_balance).quantize(MONEY_QUANTUM)
    conversion_changed = any(
        field in values for field in ("reported_balance", "converted_balance", "fx_rate")
    )
    if conversion_changed:
        converted, rate, status = _resolve_snapshot_conversion(
            amount,
            model.currency,
            model.base_currency,
            values.get("converted_balance"),
            values.get("fx_rate"),
        )
        model.reported_balance = amount
        model.converted_balance = converted
        model.fx_rate = rate
        model.fx_rate_status = status
    if "valuation_date" in values:
        model.valuation_date = values["valuation_date"]
    if "notes" in values:
        model.notes = values["notes"]
    _commit(db, "account_snapshot_date_exists")
    db.refresh(model)
    return snapshot_values(db, account, model)


def calculated_account_balance(
    db: DbSession, account: Account, through_date
) -> tuple[Decimal | None, str]:
    balance = (
        account.opening_balance.quantize(MONEY_QUANTUM)
        if account.opening_balance_date <= through_date
        else Decimal("0.0000")
    )
    transactions = list(
        db.scalars(
            select(Transaction).where(
                Transaction.account_id == account.account_id,
                Transaction.status == "active",
                Transaction.posting_date <= through_date,
            )
        )
    )
    transfer_ids = [
        item.transaction_id for item in transactions if item.transaction_kind == "transfer"
    ]
    outgoing: set[int] = set()
    incoming: set[int] = set()
    if transfer_ids:
        links = db.scalars(
            select(TransferLink).where(
                or_(
                    TransferLink.outgoing_transaction_id.in_(transfer_ids),
                    TransferLink.incoming_transaction_id.in_(transfer_ids),
                )
            )
        )
        for link in links:
            outgoing.add(link.outgoing_transaction_id)
            incoming.add(link.incoming_transaction_id)
    for transaction in transactions:
        amount = _amount_in_account_currency(transaction, account)
        if amount is None:
            return None, "incomplete"
        if transaction.transaction_kind == "expense" or transaction.transaction_id in outgoing:
            balance -= amount
        elif (
            transaction.transaction_kind in {"income", "refund", "reimbursement"}
            or transaction.transaction_id in incoming
        ):
            balance += amount
        elif transaction.transaction_kind == "adjustment":
            if transaction.adjustment_direction == "increase":
                balance += amount
            elif transaction.adjustment_direction == "decrease":
                balance -= amount
    return balance.quantize(MONEY_QUANTUM), "complete"


def snapshot_values(db: DbSession, account: Account, model: AccountSnapshot) -> dict[str, object]:
    calculated, calculation_status = calculated_account_balance(
        db, account, model.valuation_date
    )
    return {
        "account_snapshot_id": model.account_snapshot_id,
        "account_id": model.account_id,
        "valuation_date": model.valuation_date,
        "reported_balance": model.reported_balance,
        "currency": model.currency,
        "converted_balance": model.converted_balance,
        "base_currency": model.base_currency,
        "fx_rate": model.fx_rate,
        "fx_rate_status": model.fx_rate_status,
        "calculated_balance": calculated,
        "difference": (
            (model.reported_balance - calculated).quantize(MONEY_QUANTUM)
            if calculated is not None
            else None
        ),
        "calculation_status": calculation_status,
        "notes": model.notes,
        "status": model.status,
        "archived_at": model.archived_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _resolve_snapshot_conversion(
    amount: Decimal,
    currency: str,
    base_currency: str,
    converted_balance: Decimal | None,
    fx_rate: Decimal | None,
) -> tuple[Decimal | None, Decimal | None, str]:
    if currency == base_currency:
        if converted_balance is not None and converted_balance.quantize(MONEY_QUANTUM) != amount:
            raise ApiError(
                422,
                "same_currency_conversion_mismatch",
                "Converted balance must equal reported balance when currencies match.",
            )
        if fx_rate is not None and fx_rate.quantize(RATE_QUANTUM) != Decimal("1").quantize(
            RATE_QUANTUM
        ):
            raise ApiError(
                422, "same_currency_rate_mismatch", "FX rate must be 1 when currencies match."
            )
        return amount, Decimal("1").quantize(RATE_QUANTUM), "not_required"
    if converted_balance is None and fx_rate is None:
        return None, None, "missing"
    if amount == 0 and fx_rate is None:
        raise ApiError(
            422, "zero_balance_rate_required", "An FX rate is required to convert a zero balance."
        )
    if fx_rate is None:
        assert converted_balance is not None
        converted_balance = converted_balance.quantize(MONEY_QUANTUM)
        fx_rate = (converted_balance / amount).quantize(RATE_QUANTUM, rounding=ROUND_HALF_UP)
    elif converted_balance is None:
        fx_rate = fx_rate.quantize(RATE_QUANTUM)
        converted_balance = (amount * fx_rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    else:
        fx_rate = fx_rate.quantize(RATE_QUANTUM)
        converted_balance = converted_balance.quantize(MONEY_QUANTUM)
        expected = (amount * fx_rate).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        if converted_balance != expected:
            raise ApiError(
                422,
                "fx_conversion_mismatch",
                "Converted balance does not match reported balance multiplied by the FX rate.",
                [{"expected_converted_balance": str(expected)}],
            )
    if fx_rate <= 0:
        raise ApiError(422, "fx_rate_not_positive", "FX rate must be greater than zero.")
    return converted_balance, fx_rate, "manual"


def _validate_snapshot_date(account: Account, valuation_date) -> None:
    if valuation_date < account.opening_balance_date:
        raise ApiError(
            422,
            "snapshot_before_account_opening",
            "A snapshot cannot predate the account opening balance.",
        )


def _amount_in_account_currency(
    transaction: Transaction, account: Account
) -> Decimal | None:
    if transaction.original_currency == account.currency:
        return transaction.original_amount.quantize(MONEY_QUANTUM)
    if transaction.base_currency == account.currency and transaction.converted_amount is not None:
        return transaction.converted_amount.quantize(MONEY_QUANTUM)
    return None
