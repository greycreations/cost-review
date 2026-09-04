from __future__ import annotations

import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.audit_services import record_pending_audits
from app.errors import ApiError
from app.ledger_schemas import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryLinkCreate,
    CategoryUpdate,
    ProviderAliasCreate,
    ProviderAliasUpdate,
    ProviderCreate,
    ProviderLinkCreate,
    ProviderUpdate,
    SharingPartyCreate,
    SharingPartyUpdate,
    TagCreate,
    TagUpdate,
    _validate_lock_dates,
)
from app.models import (
    Account,
    Category,
    CategoryLink,
    Provider,
    ProviderAlias,
    ProviderLink,
    SharingParty,
    Tag,
)


def normalize_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).strip().casefold().split())


def list_models(
    db: DbSession,
    model: type[Any],
    *,
    limit: int,
    offset: int,
    include_archived: bool,
    search: str | None,
) -> dict[str, Any]:
    filters = []
    if not include_archived:
        filters.append(model.status == "active")  # type: ignore[attr-defined]
    if search:
        filters.append(
            model.normalized_name.contains(normalize_name(search), autoescape=True)  # type: ignore[attr-defined]
        )
    count_statement = select(func.count()).select_from(model).where(*filters)
    statement = (
        select(model)
        .where(*filters)
        .order_by(model.status, model.normalized_name, _primary_key(model))  # type: ignore[attr-defined]
        .limit(limit)
        .offset(offset)
    )
    return {
        "items": list(db.scalars(statement)),
        "total": db.scalar(count_statement) or 0,
        "limit": limit,
        "offset": offset,
    }


def get_model[ModelT](db: DbSession, model: type[ModelT], model_id: int, resource: str) -> ModelT:
    instance = db.get(model, model_id)
    if instance is None:
        raise ApiError(404, "not_found", f"{resource} was not found.")
    return instance


def create_account(db: DbSession, payload: AccountCreate) -> Account:
    values = payload.model_dump(mode="python")
    values["normalized_name"] = normalize_name(payload.name)
    model = Account(**values)
    db.add(model)
    _commit(db)
    db.refresh(model)
    return model


def update_account(db: DbSession, model: Account, payload: AccountUpdate) -> Account:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(
        values,
        {
            "name",
            "account_type",
            "opening_balance",
            "opening_balance_date",
            "currency",
            "is_locked",
        },
    )
    lock_start = values.get("lock_start_date", model.lock_start_date)
    lock_end = values.get("lock_end_date", model.lock_end_date)
    try:
        _validate_lock_dates(lock_start, lock_end)
    except ValueError as error:
        raise ApiError(422, "invalid_lock_dates", str(error)) from error
    if "name" in values:
        values["normalized_name"] = normalize_name(values["name"])
    _apply(model, values)
    _commit(db)
    db.refresh(model)
    return model


def create_category(db: DbSession, payload: CategoryCreate) -> Category:
    if payload.parent_category_id is not None:
        _require_active(
            get_model(db, Category, payload.parent_category_id, "Parent category"),
            "Parent category",
        )
    model = Category(
        **payload.model_dump(mode="python"),
        normalized_name=normalize_name(payload.name),
    )
    db.add(model)
    _commit(db)
    db.refresh(model)
    return model


def update_category(db: DbSession, model: Category, payload: CategoryUpdate) -> Category:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(values, {"name", "category_kind"})
    if "parent_category_id" in values:
        ensure_category_parent(db, model.category_id, values["parent_category_id"])
    if "name" in values:
        values["normalized_name"] = normalize_name(values["name"])
    _apply(model, values)
    _commit(db, "category_hierarchy_conflict")
    db.refresh(model)
    return model


def ensure_category_parent(db: DbSession, category_id: int, parent_id: int | None) -> None:
    seen: set[int] = set()
    current_id = parent_id
    while current_id is not None:
        if current_id == category_id:
            raise ApiError(
                409,
                "category_hierarchy_cycle",
                "A category cannot be moved below itself or one of its descendants.",
            )
        if current_id in seen:
            raise RuntimeError("existing category hierarchy contains a cycle")
        seen.add(current_id)
        current = get_model(db, Category, current_id, "Parent category")
        _require_active(current, "Parent category")
        current_id = current.parent_category_id


def archive_category(db: DbSession, model: Category) -> Category:
    active_children = db.scalar(
        select(func.count(Category.category_id)).where(
            Category.parent_category_id == model.category_id,
            Category.status == "active",
        )
    )
    if active_children:
        raise ApiError(
            409,
            "category_has_active_children",
            "Archive or move active child categories before archiving this category.",
            [{"active_child_count": active_children}],
        )
    return archive_model(db, model)


def restore_category_model(db: DbSession, model: Category) -> Category:
    if model.parent_category_id is not None:
        _require_active(
            get_model(db, Category, model.parent_category_id, "Parent category"),
            "Parent category",
        )
    return restore_model(db, model)


def create_category_link(db: DbSession, payload: CategoryLinkCreate) -> CategoryLink:
    lower_id, higher_id = _canonical_pair(
        payload.first_category_id, payload.second_category_id, "category"
    )
    _require_active(get_model(db, Category, lower_id, "Category"), "Category")
    _require_active(get_model(db, Category, higher_id, "Category"), "Category")
    model = CategoryLink(
        lower_category_id=lower_id,
        higher_category_id=higher_id,
        label=payload.label,
    )
    db.add(model)
    _commit(db, "category_link_exists")
    db.refresh(model)
    return model


def create_provider(db: DbSession, payload: ProviderCreate) -> Provider:
    model = Provider(
        **payload.model_dump(mode="python"),
        normalized_name=normalize_name(payload.name),
    )
    db.add(model)
    _commit(db)
    db.refresh(model)
    return model


def update_provider(db: DbSession, model: Provider, payload: ProviderUpdate) -> Provider:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(values, {"name"})
    if "name" in values:
        values["normalized_name"] = normalize_name(values["name"])
    _apply(model, values)
    _commit(db)
    db.refresh(model)
    return model


def create_provider_alias(
    db: DbSession, provider: Provider, payload: ProviderAliasCreate
) -> ProviderAlias:
    _require_active(provider, "Provider")
    normalized = normalize_name(payload.alias)
    existing = db.scalar(select(ProviderAlias).where(ProviderAlias.normalized_alias == normalized))
    if existing is not None:
        raise ApiError(
            409,
            "provider_alias_exists",
            "This alias is already assigned to a provider.",
            [{"provider_id": existing.provider_id}],
        )
    model = ProviderAlias(
        provider_id=provider.provider_id,
        alias=payload.alias,
        normalized_alias=normalized,
    )
    db.add(model)
    _commit(db, "provider_alias_exists")
    db.refresh(model)
    return model


def update_provider_alias(
    db: DbSession, model: ProviderAlias, payload: ProviderAliasUpdate
) -> ProviderAlias:
    normalized = normalize_name(payload.alias)
    existing = db.scalar(
        select(ProviderAlias).where(
            ProviderAlias.normalized_alias == normalized,
            ProviderAlias.provider_alias_id != model.provider_alias_id,
        )
    )
    if existing is not None:
        raise ApiError(
            409,
            "provider_alias_exists",
            "This alias is already assigned to a provider.",
            [{"provider_id": existing.provider_id}],
        )
    model.alias = payload.alias
    model.normalized_alias = normalized
    _commit(db, "provider_alias_exists")
    db.refresh(model)
    return model


def create_provider_link(db: DbSession, payload: ProviderLinkCreate) -> ProviderLink:
    lower_id, higher_id = _canonical_pair(
        payload.first_provider_id, payload.second_provider_id, "provider"
    )
    _require_active(get_model(db, Provider, lower_id, "Provider"), "Provider")
    _require_active(get_model(db, Provider, higher_id, "Provider"), "Provider")
    model = ProviderLink(
        lower_provider_id=lower_id,
        higher_provider_id=higher_id,
        label=payload.label,
    )
    db.add(model)
    _commit(db, "provider_link_exists")
    db.refresh(model)
    return model


def create_tag(db: DbSession, payload: TagCreate) -> Tag:
    model = Tag(
        **payload.model_dump(mode="python"),
        normalized_name=normalize_name(payload.name),
    )
    db.add(model)
    _commit(db, "tag_name_exists")
    db.refresh(model)
    return model


def update_tag(db: DbSession, model: Tag, payload: TagUpdate) -> Tag:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(values, {"name"})
    if "name" in values:
        values["normalized_name"] = normalize_name(values["name"])
    _apply(model, values)
    _commit(db, "tag_name_exists")
    db.refresh(model)
    return model


def create_sharing_party(db: DbSession, payload: SharingPartyCreate) -> SharingParty:
    if payload.is_self:
        _ensure_no_active_self(db)
    model = SharingParty(
        **payload.model_dump(mode="python"),
        normalized_name=normalize_name(payload.name),
    )
    db.add(model)
    _commit(db, "active_self_exists")
    db.refresh(model)
    return model


def update_sharing_party(
    db: DbSession, model: SharingParty, payload: SharingPartyUpdate
) -> SharingParty:
    values = payload.model_dump(exclude_unset=True, mode="python")
    _reject_nulls(values, {"name", "is_self"})
    if values.get("is_self") is True and not model.is_self and model.status == "active":
        _ensure_no_active_self(db, exclude_id=model.sharing_party_id)
    if "name" in values:
        values["normalized_name"] = normalize_name(values["name"])
    _apply(model, values)
    _commit(db, "active_self_exists")
    db.refresh(model)
    return model


def archive_model[ModelT](db: DbSession, model: ModelT) -> ModelT:
    if model.status == "active":  # type: ignore[attr-defined]
        model.status = "archived"  # type: ignore[attr-defined]
        model.archived_at = datetime.now(UTC)  # type: ignore[attr-defined]
        _commit(db)
        db.refresh(model)
    return model


def restore_model[ModelT](db: DbSession, model: ModelT) -> ModelT:
    if isinstance(model, SharingParty) and model.is_self:
        _ensure_no_active_self(db, exclude_id=model.sharing_party_id)
    if model.status == "archived":  # type: ignore[attr-defined]
        model.status = "active"  # type: ignore[attr-defined]
        model.archived_at = None  # type: ignore[attr-defined]
        _commit(db, "restore_conflict")
        db.refresh(model)
    return model


def delete_configuration_model(db: DbSession, model: Any) -> None:
    db.delete(model)
    _commit(db)


def _ensure_no_active_self(db: DbSession, exclude_id: int | None = None) -> None:
    statement = select(SharingParty).where(
        SharingParty.is_self.is_(True),
        SharingParty.status == "active",
    )
    if exclude_id is not None:
        statement = statement.where(SharingParty.sharing_party_id != exclude_id)
    if db.scalar(statement) is not None:
        raise ApiError(
            409,
            "active_self_exists",
            "Only one active sharing party can represent the signed-in owner.",
        )


def _canonical_pair(first_id: int, second_id: int, resource: str) -> tuple[int, int]:
    if first_id == second_id:
        raise ApiError(
            422,
            f"{resource}_link_self_reference",
            f"A {resource} cannot be linked to itself.",
        )
    return min(first_id, second_id), max(first_id, second_id)


def _require_active(model: Any, resource: str) -> None:
    if model.status != "active":
        raise ApiError(
            409,
            "archived_dependency",
            f"{resource} is archived and cannot be used by an active record.",
        )


def _primary_key(model: type[Any]):
    return next(iter(model.__table__.primary_key.columns))


def _reject_nulls(values: dict[str, Any], required_fields: set[str]) -> None:
    invalid = sorted(
        field for field in required_fields if field in values and values[field] is None
    )
    if invalid:
        raise ApiError(
            422,
            "required_field_null",
            "Required fields cannot be null.",
            [{"fields": invalid}],
        )


def _apply(model: Any, values: dict[str, Any]) -> None:
    for field_name, value in values.items():
        setattr(model, field_name, value)


def _commit(db: DbSession, conflict_code: str = "ledger_conflict") -> None:
    try:
        record_pending_audits(db)
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint_name = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
        raise ApiError(
            409,
            conflict_code,
            "The change conflicts with existing ledger data or integrity rules.",
            [{"constraint": constraint_name}] if constraint_name else None,
        ) from error
