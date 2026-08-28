from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.dependencies import Auth, CsrfAuth, DatabaseSession
from app.ledger_schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    CategoryCreate,
    CategoryLinkCreate,
    CategoryLinkRead,
    CategoryRead,
    CategoryUpdate,
    Page,
    ProviderAliasCreate,
    ProviderAliasRead,
    ProviderAliasUpdate,
    ProviderCreate,
    ProviderLinkCreate,
    ProviderLinkRead,
    ProviderRead,
    ProviderUpdate,
    SharingPartyCreate,
    SharingPartyRead,
    SharingPartyUpdate,
    TagCreate,
    TagRead,
    TagUpdate,
)
from app.ledger_services import (
    archive_category,
    archive_model,
    create_account,
    create_category,
    create_category_link,
    create_provider,
    create_provider_alias,
    create_provider_link,
    create_sharing_party,
    create_tag,
    delete_configuration_model,
    get_model,
    list_models,
    restore_category_model,
    restore_model,
    update_account,
    update_category,
    update_provider,
    update_provider_alias,
    update_sharing_party,
    update_tag,
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

router = APIRouter(tags=["ledger-master-data"])

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


@router.get("/accounts", response_model=Page[AccountRead])
def list_accounts(
    _: Auth,
    db: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
    include_archived: bool = False,
    search: str | None = Query(default=None, max_length=120),
) -> dict[str, object]:
    return list_models(
        db,
        Account,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        search=search,
    )


@router.post("/accounts", response_model=AccountRead, status_code=201)
def post_account(payload: AccountCreate, _: CsrfAuth, db: DatabaseSession) -> Account:
    return create_account(db, payload)


@router.get("/accounts/{account_id}", response_model=AccountRead)
def get_account(account_id: int, _: Auth, db: DatabaseSession) -> Account:
    return get_model(db, Account, account_id, "Account")


@router.patch("/accounts/{account_id}", response_model=AccountRead)
def patch_account(
    account_id: int, payload: AccountUpdate, _: CsrfAuth, db: DatabaseSession
) -> Account:
    return update_account(db, get_model(db, Account, account_id, "Account"), payload)


@router.post("/accounts/{account_id}/archive", response_model=AccountRead)
def archive_account(account_id: int, _: CsrfAuth, db: DatabaseSession) -> Account:
    return archive_model(db, get_model(db, Account, account_id, "Account"))


@router.post("/accounts/{account_id}/restore", response_model=AccountRead)
def restore_account(account_id: int, _: CsrfAuth, db: DatabaseSession) -> Account:
    return restore_model(db, get_model(db, Account, account_id, "Account"))


@router.get("/categories", response_model=Page[CategoryRead])
def list_categories(
    _: Auth,
    db: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
    include_archived: bool = False,
    search: str | None = Query(default=None, max_length=120),
) -> dict[str, object]:
    return list_models(
        db,
        Category,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        search=search,
    )


@router.post("/categories", response_model=CategoryRead, status_code=201)
def post_category(payload: CategoryCreate, _: CsrfAuth, db: DatabaseSession) -> Category:
    return create_category(db, payload)


@router.get("/categories/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, _: Auth, db: DatabaseSession) -> Category:
    return get_model(db, Category, category_id, "Category")


@router.patch("/categories/{category_id}", response_model=CategoryRead)
def patch_category(
    category_id: int, payload: CategoryUpdate, _: CsrfAuth, db: DatabaseSession
) -> Category:
    return update_category(db, get_model(db, Category, category_id, "Category"), payload)


@router.post("/categories/{category_id}/archive", response_model=CategoryRead)
def post_archive_category(category_id: int, _: CsrfAuth, db: DatabaseSession) -> Category:
    return archive_category(db, get_model(db, Category, category_id, "Category"))


@router.post("/categories/{category_id}/restore", response_model=CategoryRead)
def restore_category(category_id: int, _: CsrfAuth, db: DatabaseSession) -> Category:
    return restore_category_model(db, get_model(db, Category, category_id, "Category"))


@router.get("/category-links", response_model=Page[CategoryLinkRead])
def list_category_links(
    _: Auth, db: DatabaseSession, limit: Limit = 50, offset: Offset = 0
) -> dict[str, object]:
    return _plain_page(db, CategoryLink, limit, offset)


@router.post("/category-links", response_model=CategoryLinkRead, status_code=201)
def post_category_link(
    payload: CategoryLinkCreate, _: CsrfAuth, db: DatabaseSession
) -> CategoryLink:
    return create_category_link(db, payload)


@router.delete("/category-links/{link_id}", status_code=204)
def delete_category_link(link_id: int, _: CsrfAuth, db: DatabaseSession) -> Response:
    delete_configuration_model(db, get_model(db, CategoryLink, link_id, "Category link"))
    return Response(status_code=204)


@router.get("/providers", response_model=Page[ProviderRead])
def list_providers(
    _: Auth,
    db: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
    include_archived: bool = False,
    search: str | None = Query(default=None, max_length=160),
) -> dict[str, object]:
    return list_models(
        db,
        Provider,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        search=search,
    )


@router.post("/providers", response_model=ProviderRead, status_code=201)
def post_provider(payload: ProviderCreate, _: CsrfAuth, db: DatabaseSession) -> Provider:
    return create_provider(db, payload)


@router.get("/providers/{provider_id}", response_model=ProviderRead)
def get_provider(provider_id: int, _: Auth, db: DatabaseSession) -> Provider:
    return get_model(db, Provider, provider_id, "Provider")


@router.patch("/providers/{provider_id}", response_model=ProviderRead)
def patch_provider(
    provider_id: int, payload: ProviderUpdate, _: CsrfAuth, db: DatabaseSession
) -> Provider:
    return update_provider(db, get_model(db, Provider, provider_id, "Provider"), payload)


@router.post("/providers/{provider_id}/archive", response_model=ProviderRead)
def archive_provider(provider_id: int, _: CsrfAuth, db: DatabaseSession) -> Provider:
    return archive_model(db, get_model(db, Provider, provider_id, "Provider"))


@router.post("/providers/{provider_id}/restore", response_model=ProviderRead)
def restore_provider(provider_id: int, _: CsrfAuth, db: DatabaseSession) -> Provider:
    return restore_model(db, get_model(db, Provider, provider_id, "Provider"))


@router.get("/providers/{provider_id}/aliases", response_model=Page[ProviderAliasRead])
def list_provider_aliases(
    provider_id: int, _: Auth, db: DatabaseSession, limit: Limit = 50, offset: Offset = 0
) -> dict[str, object]:
    get_model(db, Provider, provider_id, "Provider")
    return _plain_page(
        db,
        ProviderAlias,
        limit,
        offset,
        ProviderAlias.provider_id == provider_id,
    )


@router.post("/providers/{provider_id}/aliases", response_model=ProviderAliasRead, status_code=201)
def post_provider_alias(
    provider_id: int, payload: ProviderAliasCreate, _: CsrfAuth, db: DatabaseSession
) -> ProviderAlias:
    provider = get_model(db, Provider, provider_id, "Provider")
    return create_provider_alias(db, provider, payload)


@router.patch("/provider-aliases/{alias_id}", response_model=ProviderAliasRead)
def patch_provider_alias(
    alias_id: int, payload: ProviderAliasUpdate, _: CsrfAuth, db: DatabaseSession
) -> ProviderAlias:
    return update_provider_alias(
        db, get_model(db, ProviderAlias, alias_id, "Provider alias"), payload
    )


@router.delete("/provider-aliases/{alias_id}", status_code=204)
def delete_provider_alias(alias_id: int, _: CsrfAuth, db: DatabaseSession) -> Response:
    delete_configuration_model(db, get_model(db, ProviderAlias, alias_id, "Provider alias"))
    return Response(status_code=204)


@router.get("/provider-links", response_model=Page[ProviderLinkRead])
def list_provider_links(
    _: Auth, db: DatabaseSession, limit: Limit = 50, offset: Offset = 0
) -> dict[str, object]:
    return _plain_page(db, ProviderLink, limit, offset)


@router.post("/provider-links", response_model=ProviderLinkRead, status_code=201)
def post_provider_link(
    payload: ProviderLinkCreate, _: CsrfAuth, db: DatabaseSession
) -> ProviderLink:
    return create_provider_link(db, payload)


@router.delete("/provider-links/{link_id}", status_code=204)
def delete_provider_link(link_id: int, _: CsrfAuth, db: DatabaseSession) -> Response:
    delete_configuration_model(db, get_model(db, ProviderLink, link_id, "Provider link"))
    return Response(status_code=204)


@router.get("/tags", response_model=Page[TagRead])
def list_tags(
    _: Auth,
    db: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
    include_archived: bool = False,
    search: str | None = Query(default=None, max_length=80),
) -> dict[str, object]:
    return list_models(
        db,
        Tag,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        search=search,
    )


@router.post("/tags", response_model=TagRead, status_code=201)
def post_tag(payload: TagCreate, _: CsrfAuth, db: DatabaseSession) -> Tag:
    return create_tag(db, payload)


@router.get("/tags/{tag_id}", response_model=TagRead)
def get_tag(tag_id: int, _: Auth, db: DatabaseSession) -> Tag:
    return get_model(db, Tag, tag_id, "Tag")


@router.patch("/tags/{tag_id}", response_model=TagRead)
def patch_tag(tag_id: int, payload: TagUpdate, _: CsrfAuth, db: DatabaseSession) -> Tag:
    return update_tag(db, get_model(db, Tag, tag_id, "Tag"), payload)


@router.post("/tags/{tag_id}/archive", response_model=TagRead)
def archive_tag(tag_id: int, _: CsrfAuth, db: DatabaseSession) -> Tag:
    return archive_model(db, get_model(db, Tag, tag_id, "Tag"))


@router.post("/tags/{tag_id}/restore", response_model=TagRead)
def restore_tag(tag_id: int, _: CsrfAuth, db: DatabaseSession) -> Tag:
    return restore_model(db, get_model(db, Tag, tag_id, "Tag"))


@router.get("/sharing-parties", response_model=Page[SharingPartyRead])
def list_sharing_parties(
    _: Auth,
    db: DatabaseSession,
    limit: Limit = 50,
    offset: Offset = 0,
    include_archived: bool = False,
    search: str | None = Query(default=None, max_length=120),
) -> dict[str, object]:
    return list_models(
        db,
        SharingParty,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
        search=search,
    )


@router.post("/sharing-parties", response_model=SharingPartyRead, status_code=201)
def post_sharing_party(
    payload: SharingPartyCreate, _: CsrfAuth, db: DatabaseSession
) -> SharingParty:
    return create_sharing_party(db, payload)


@router.get("/sharing-parties/{party_id}", response_model=SharingPartyRead)
def get_sharing_party(party_id: int, _: Auth, db: DatabaseSession) -> SharingParty:
    return get_model(db, SharingParty, party_id, "Sharing party")


@router.patch("/sharing-parties/{party_id}", response_model=SharingPartyRead)
def patch_sharing_party(
    party_id: int, payload: SharingPartyUpdate, _: CsrfAuth, db: DatabaseSession
) -> SharingParty:
    return update_sharing_party(db, get_model(db, SharingParty, party_id, "Sharing party"), payload)


@router.post("/sharing-parties/{party_id}/archive", response_model=SharingPartyRead)
def archive_sharing_party(party_id: int, _: CsrfAuth, db: DatabaseSession) -> SharingParty:
    return archive_model(db, get_model(db, SharingParty, party_id, "Sharing party"))


@router.post("/sharing-parties/{party_id}/restore", response_model=SharingPartyRead)
def restore_sharing_party(party_id: int, _: CsrfAuth, db: DatabaseSession) -> SharingParty:
    return restore_model(db, get_model(db, SharingParty, party_id, "Sharing party"))


def _plain_page(
    db: DbSession,
    model,
    limit: int,
    offset: int,
    *filters,
) -> dict[str, object]:
    total = db.scalar(select(func.count()).select_from(model).where(*filters)) or 0
    primary_key = next(iter(model.__table__.primary_key.columns))
    items = list(
        db.scalars(select(model).where(*filters).order_by(primary_key).limit(limit).offset(offset))
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}
