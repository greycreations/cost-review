from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session as DbSession

from app.models import (
    Account,
    AccountSnapshot,
    AnalysisGroup,
    AuditEvent,
    Budget,
    Category,
    Provider,
    SharingParty,
    Tag,
    Transaction,
)

AUDITED_TYPES = (
    Account,
    AccountSnapshot,
    AnalysisGroup,
    Budget,
    Category,
    Provider,
    SharingParty,
    Tag,
    Transaction,
)


def record_audit(
    db: DbSession,
    *,
    entity_type: str,
    entity_id: int | None,
    action: str,
    changes: dict[str, Any],
    source: str = "user",
) -> AuditEvent:
    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        change_source=source,
        changes=_json_value(changes),
    )
    db.add(event)
    return event


def record_model_created(db: DbSession, model: Any) -> AuditEvent:
    """Record a model that had to be flushed before the shared commit hook."""
    return record_audit(
        db,
        entity_type=_entity_type(model),
        entity_id=_entity_id(model),
        action="created",
        changes=_column_values(model),
    )


def list_audit_events(
    db: DbSession,
    *,
    limit: int,
    offset: int,
    entity_type: str | None = None,
    entity_id: int | None = None,
) -> dict[str, object]:
    filters = []
    if entity_type is not None:
        filters.append(AuditEvent.entity_type == entity_type)
    if entity_id is not None:
        filters.append(AuditEvent.entity_id == entity_id)
    total = db.scalar(select(func.count()).select_from(AuditEvent).where(*filters)) or 0
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(*filters)
            .order_by(AuditEvent.created_at.desc(), AuditEvent.audit_event_id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return {"items": events, "total": total, "limit": limit, "offset": offset}


def record_pending_audits(db: DbSession) -> None:
    created = [model for model in db.new if isinstance(model, AUDITED_TYPES)]
    updates: list[tuple[Any, str, dict[str, Any]]] = []
    for model in db.dirty:
        if not isinstance(model, AUDITED_TYPES) or model in created:
            continue
        changes: dict[str, Any] = {}
        state = inspect(model)
        for attribute in state.mapper.column_attrs:
            history = state.attrs[attribute.key].history
            if not history.has_changes():
                continue
            changes[attribute.key] = {
                "old": history.deleted[0] if history.deleted else None,
                "new": history.added[0] if history.added else getattr(model, attribute.key),
            }
        if not changes:
            continue
        status_change = changes.get("status")
        if status_change and status_change["new"] == "archived":
            action = "archived"
        elif status_change and status_change["new"] == "active":
            action = "restored"
        else:
            action = "updated"
        updates.append((model, action, changes))

    if not created and not updates:
        return
    db.flush()
    for model in created:
        record_audit(
            db,
            entity_type=_entity_type(model),
            entity_id=_entity_id(model),
            action="created",
            changes=_column_values(model),
        )
    for model, action, changes in updates:
        record_audit(
            db,
            entity_type=_entity_type(model),
            entity_id=_entity_id(model),
            action=action,
            changes=changes,
        )


def _entity_type(model: Any) -> str:
    name = type(model).__name__
    snake_case = "".join(
        f"_{character.lower()}" if character.isupper() else character
        for character in name
    )
    return snake_case.lstrip("_")


def _entity_id(model: Any) -> int | None:
    identity = inspect(model).identity
    return int(identity[0]) if identity else None


def _column_values(model: Any) -> dict[str, Any]:
    state = inspect(model)
    return {
        attribute.key: getattr(model, attribute.key)
        for attribute in state.mapper.column_attrs
        if attribute.key not in {"password_hash"}
    }


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, (date, datetime, Decimal, UUID, Enum)):
        return str(value.value if isinstance(value, Enum) else value)
    return value
