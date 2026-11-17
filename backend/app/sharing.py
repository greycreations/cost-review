"""Shared Total / My Share semantics for every analytical surface.

The household ledger is common to all members of a data plane. "My Share" is
therefore personal: it is the portion allocated to the sharing party linked to
the requesting user. Ledger summaries, analysis and budgets must use the same
rules, so they live here instead of being repeated per service.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.models import SharingParty, TransactionSplit

HUNDRED = Decimal("100")


@dataclass(frozen=True, slots=True)
class Perspective:
    """Which part of an economic event an analysis counts.

    ``kind`` is ``"total"`` or ``"my_share"``. For ``my_share``,
    ``self_party_id`` identifies the active sharing party linked to the
    requesting user; ``None`` means that user has no linked party.
    """

    kind: str = "total"
    self_party_id: int | None = None

    @property
    def is_total(self) -> bool:
        return self.kind == "total"


TOTAL = Perspective()


def perspective_for_user(db: DbSession, kind: str, user_id: int) -> Perspective:
    if kind == "total":
        return TOTAL
    party_id = db.scalar(
        select(SharingParty.sharing_party_id).where(
            SharingParty.user_id == user_id,
            SharingParty.status == "active",
        )
    )
    return Perspective(kind=kind, self_party_id=party_id)


def share_multiplier(split: TransactionSplit, perspective: Perspective) -> Decimal:
    """Fraction of a split that belongs to the perspective.

    A split without allocations is not shared and belongs fully to the
    household view and to every member's view, matching earlier releases.
    """

    if perspective.is_total or not split.share_allocations:
        return Decimal("1")
    if perspective.self_party_id is None:
        return Decimal("0")
    return (
        sum(
            (
                allocation.percentage
                for allocation in split.share_allocations
                if allocation.sharing_party_id == perspective.self_party_id
            ),
            Decimal("0"),
        )
        / HUNDRED
    )


def share_allocation_values(split: TransactionSplit) -> list[dict[str, Any]]:
    return [
        {
            "sharing_party_id": allocation.sharing_party_id,
            "percentage": allocation.percentage,
            "user_id": allocation.sharing_party.user_id,
        }
        for allocation in sorted(
            split.share_allocations, key=lambda item: item.sharing_party_id
        )
    ]
