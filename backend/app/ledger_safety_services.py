from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.account_snapshot_services import snapshot_values
from app.audit_services import record_audit
from app.errors import ApiError
from app.models import (
    Account,
    AccountSnapshot,
    AnalysisGroup,
    Budget,
    Category,
    Provider,
    SharingParty,
    Tag,
    Transaction,
    TransactionKind,
    TransactionSplit,
    TransferLink,
)
from app.transaction_services import MONEY_QUANTUM, normalize_name

ADJUSTMENT_CONFIRMATION = "CREATE BALANCE ADJUSTMENT"


def create_balance_adjustment(
    db: DbSession,
    snapshot: AccountSnapshot,
    account: Account,
    *,
    confirmation: str,
) -> Transaction:
    if confirmation != ADJUSTMENT_CONFIRMATION:
        raise ApiError(
            422,
            "confirmation_mismatch",
            f"Type {ADJUSTMENT_CONFIRMATION} exactly to create the adjustment.",
        )
    if snapshot.status != "active" or account.status != "active":
        raise ApiError(
            409,
            "archived_dependency",
            "An active account and snapshot are required for reconciliation.",
        )
    source_reference = f"account-snapshot:{snapshot.account_snapshot_id}"
    existing = db.scalar(
        select(Transaction).where(
            Transaction.transaction_kind == TransactionKind.ADJUSTMENT,
            Transaction.source_reference == source_reference,
        )
    )
    if existing is not None:
        raise ApiError(
            409,
            "snapshot_already_adjusted",
            "This account snapshot already has a balance adjustment.",
            [{"transaction_id": existing.transaction_id}],
        )

    reconciliation = snapshot_values(db, account, snapshot)
    difference = reconciliation["difference"]
    if not isinstance(difference, Decimal):
        raise ApiError(
            409,
            "reconciliation_incomplete",
            "The calculated balance is incomplete; resolve missing currency values first.",
        )
    difference = difference.quantize(MONEY_QUANTUM)
    if difference == 0:
        raise ApiError(
            409,
            "account_already_reconciled",
            "The reported and calculated balances already match.",
        )

    original_amount = abs(difference)
    if account.currency == snapshot.base_currency:
        converted_amount = original_amount
        fx_rate = Decimal("1.0000000000")
        fx_rate_status = "not_required"
    elif snapshot.fx_rate is not None:
        fx_rate = snapshot.fx_rate
        converted_amount = (original_amount * fx_rate).quantize(MONEY_QUANTUM)
        fx_rate_status = snapshot.fx_rate_status
    else:
        converted_amount = None
        fx_rate = None
        fx_rate_status = "missing"

    model = Transaction(
        account_id=account.account_id,
        provider_id=None,
        transaction_kind=TransactionKind.ADJUSTMENT,
        adjustment_direction="increase" if difference > 0 else "decrease",
        transaction_date=snapshot.valuation_date,
        posting_date=snapshot.valuation_date,
        description="Balance reconciliation adjustment",
        normalized_description=normalize_name("Balance reconciliation adjustment"),
        original_amount=original_amount,
        original_currency=account.currency,
        converted_amount=converted_amount,
        base_currency=snapshot.base_currency,
        fx_rate=fx_rate,
        fx_rate_status=fx_rate_status,
        source_type="system",
        source_reference=source_reference,
        notes=snapshot.notes,
        splits=[
            TransactionSplit(
                category_id=None,
                original_amount=original_amount,
                converted_amount=converted_amount,
                is_base_cost=False,
            )
        ],
    )
    db.add(model)
    db.flush()
    record_audit(
        db,
        entity_type="account_snapshot",
        entity_id=snapshot.account_snapshot_id,
        action="balance_adjusted",
        source="user",
        changes={
            "account_id": account.account_id,
            "transaction_id": model.transaction_id,
            "direction": model.adjustment_direction,
            "amount": original_amount,
            "currency": account.currency,
            "reported_balance": snapshot.reported_balance,
            "calculated_balance_before": reconciliation["calculated_balance"],
        },
    )
    db.commit()
    db.refresh(model)
    return model


def set_adjustment_archived(
    db: DbSession, model: Transaction, *, archived: bool
) -> Transaction:
    if model.transaction_kind != TransactionKind.ADJUSTMENT:
        raise ApiError(404, "not_found", "Balance adjustment was not found.")
    desired = "archived" if archived else "active"
    if model.status != desired:
        model.status = desired
        model.archived_at = datetime.now(UTC) if archived else None
        record_audit(
            db,
            entity_type="transaction",
            entity_id=model.transaction_id,
            action="archived" if archived else "restored",
            changes={"transaction_kind": "adjustment"},
        )
        db.commit()
        db.refresh(model)
    return model


def list_recycle_bin(db: DbSession) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    _append_archived(items, db, Account, "account", "account_id", "name", "/accounts/{id}/restore")
    _append_archived(
        items,
        db,
        AccountSnapshot,
        "account_snapshot",
        "account_snapshot_id",
        None,
        "/account-snapshots/{id}/restore",
        label=lambda model: f"Account snapshot · {model.valuation_date}",
    )
    _append_archived(
        items, db, Category, "category", "category_id", "name", "/categories/{id}/restore"
    )
    _append_archived(
        items, db, Provider, "provider", "provider_id", "name", "/providers/{id}/restore"
    )
    _append_archived(items, db, Tag, "tag", "tag_id", "name", "/tags/{id}/restore")
    _append_archived(
        items,
        db,
        SharingParty,
        "sharing_party",
        "sharing_party_id",
        "name",
        "/sharing-parties/{id}/restore",
    )
    _append_archived(
        items,
        db,
        AnalysisGroup,
        "analysis_group",
        "analysis_group_id",
        "name",
        "/analysis-groups/{id}/restore",
    )
    _append_archived(items, db, Budget, "budget", "budget_id", "name", "/budgets/{id}/restore")

    transfer_transaction_ids: set[int] = set()
    for link in db.scalars(select(TransferLink)):
        if link.outgoing_transaction.status == "archived":
            transfer_transaction_ids.update(
                {link.outgoing_transaction_id, link.incoming_transaction_id}
            )
            items.append(
                _item(
                    "transfer",
                    link.transfer_link_id,
                    link.outgoing_transaction.description,
                    link.outgoing_transaction.archived_at,
                    f"/transfers/{link.transfer_link_id}/restore",
                )
            )
    for model in db.scalars(
        select(Transaction).where(
            Transaction.status == "archived",
            Transaction.transaction_id.not_in(transfer_transaction_ids),
        )
    ):
        if model.transaction_kind in {"refund", "reimbursement"}:
            path = f"/recoveries/{model.transaction_id}/restore"
        elif model.transaction_kind == "adjustment":
            path = f"/adjustments/{model.transaction_id}/restore"
        else:
            path = f"/transactions/{model.transaction_id}/restore"
        items.append(
            _item(
                "transaction",
                model.transaction_id,
                model.description,
                model.archived_at,
                path,
            )
        )
    return sorted(items, key=lambda item: item["archived_at"], reverse=True)


def _append_archived(
    items: list[dict[str, Any]],
    db: DbSession,
    model_type: type[Any],
    entity_type: str,
    id_field: str,
    label_field: str | None,
    restore_path: str,
    *,
    label=None,
) -> None:
    for model in db.scalars(select(model_type).where(model_type.status == "archived")):
        text = label(model) if label is not None else getattr(model, label_field)
        entity_id = getattr(model, id_field)
        items.append(
            _item(
                entity_type,
                entity_id,
                text,
                model.archived_at,
                restore_path.format(id=entity_id),
            )
        )


def _item(
    entity_type: str,
    entity_id: int,
    label: str,
    archived_at: datetime | None,
    restore_path: str,
) -> dict[str, Any]:
    if archived_at is None:
        raise RuntimeError("archived entity is missing archived_at")
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "label": label,
        "archived_at": archived_at,
        "restore_path": restore_path,
    }
