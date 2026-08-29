from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.errors import ApiError
from app.ledger_schemas import RecoveryCreate
from app.ledger_services import archive_model, normalize_name, restore_model
from app.models import (
    Account,
    Provider,
    RefundLink,
    ReimbursementLink,
    Transaction,
    TransactionKind,
    TransactionSplit,
)
from app.transaction_services import (
    MONEY_QUANTUM,
    get_transaction,
    resolve_conversion,
    transaction_values,
)


def create_recovery(
    db: DbSession,
    original_expense: Transaction,
    payload: RecoveryCreate,
    kind: TransactionKind,
    base_currency: str,
) -> Transaction:
    if kind not in (TransactionKind.REFUND, TransactionKind.REIMBURSEMENT):
        raise ValueError("Recovery kind must be refund or reimbursement")
    if original_expense.transaction_kind != TransactionKind.EXPENSE:
        raise ApiError(422, "recovery_requires_expense", "Recoveries must link to an expense.")
    if original_expense.status != "active":
        raise ApiError(409, "archived_expense", "An archived expense cannot receive a recovery.")
    if payload.transaction_date < original_expense.transaction_date:
        raise ApiError(
            422,
            "recovery_before_expense",
            "A refund or reimbursement cannot predate the original expense.",
        )

    account = _active_dependency(db, Account, payload.account_id, "Account")
    provider = (
        _active_dependency(db, Provider, payload.provider_id, "Provider")
        if payload.provider_id is not None
        else None
    )
    amount = payload.original_amount.quantize(MONEY_QUANTUM)
    converted_amount, fx_rate, fx_rate_status = resolve_conversion(
        amount,
        payload.original_currency,
        base_currency,
        payload.converted_amount,
        payload.fx_rate,
    )
    recovery = Transaction(
        account_id=account.account_id,
        provider_id=provider.provider_id if provider is not None else None,
        transaction_kind=kind.value,
        transaction_date=payload.transaction_date,
        posting_date=payload.posting_date,
        description=payload.description,
        normalized_description=normalize_name(payload.description),
        original_amount=amount,
        original_currency=payload.original_currency,
        converted_amount=converted_amount,
        base_currency=base_currency,
        fx_rate=fx_rate,
        fx_rate_status=fx_rate_status,
        source_type="manual",
        source_reference=payload.source_reference,
        notes=payload.notes,
        splits=[
            TransactionSplit(
                category_id=None,
                original_amount=amount,
                converted_amount=converted_amount,
                is_base_cost=False,
            )
        ],
    )
    db.add(recovery)
    db.flush()
    if kind == TransactionKind.REFUND:
        db.add(
            RefundLink(
                original_expense_id=original_expense.transaction_id,
                refund_transaction_id=recovery.transaction_id,
            )
        )
    else:
        db.add(
            ReimbursementLink(
                original_expense_id=original_expense.transaction_id,
                reimbursement_transaction_id=recovery.transaction_id,
            )
        )
    _commit(db)
    return get_transaction(db, recovery.transaction_id)


def get_recovery(db: DbSession, transaction_id: int) -> tuple[Transaction, int]:
    transaction = get_transaction(db, transaction_id)
    linked_expense_id = linked_expense_ids(db, [transaction_id]).get(transaction_id)
    if (
        transaction.transaction_kind
        not in (TransactionKind.REFUND, TransactionKind.REIMBURSEMENT)
        or linked_expense_id is None
    ):
        raise ApiError(404, "not_found", "Refund or reimbursement was not found.")
    return transaction, linked_expense_id


def set_recovery_archived(
    db: DbSession, transaction: Transaction, *, archived: bool
) -> Transaction:
    return archive_model(db, transaction) if archived else restore_model(db, transaction)


def recovery_values(db: DbSession, transaction: Transaction) -> dict[str, object]:
    linked_id = linked_expense_ids(db, [transaction.transaction_id]).get(
        transaction.transaction_id
    )
    return transaction_values(transaction, linked_expense_id=linked_id)


def linked_expense_ids(db: DbSession, transaction_ids: list[int]) -> dict[int, int]:
    if not transaction_ids:
        return {}
    links = {
        recovery_id: expense_id
        for expense_id, recovery_id in db.execute(
            select(RefundLink.original_expense_id, RefundLink.refund_transaction_id).where(
                RefundLink.refund_transaction_id.in_(transaction_ids)
            )
        )
    }
    links.update(
        {
            recovery_id: expense_id
            for expense_id, recovery_id in db.execute(
                select(
                    ReimbursementLink.original_expense_id,
                    ReimbursementLink.reimbursement_transaction_id,
                ).where(ReimbursementLink.reimbursement_transaction_id.in_(transaction_ids))
            )
        }
    )
    return links


def _active_dependency(db: DbSession, model_type, model_id: int, label: str):
    model = db.get(model_type, model_id)
    if model is None:
        raise ApiError(404, "not_found", f"{label} was not found.")
    if model.status != "active":
        raise ApiError(409, "archived_dependency", f"{label} is archived.")
    return model


def _commit(db: DbSession) -> None:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        raise ApiError(
            409,
            "recovery_integrity_conflict",
            "The recovery conflicts with the original expense or existing recoveries.",
            [{"constraint": constraint_name}] if constraint_name else None,
        ) from error
