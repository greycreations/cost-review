from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models import AccountType, CategoryKind, LifecycleStatus

Name120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Name160 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Alias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class ArchivedApiModel(ApiModel):
    status: LifecycleStatus
    archived_at: datetime | None


class AccountCreate(BaseModel):
    name: Name120
    account_type: AccountType
    opening_balance: Decimal = Field(default=Decimal("0"), max_digits=20, decimal_places=4)
    opening_balance_date: date
    currency: CurrencyCode
    interest_rate: Decimal | None = Field(
        default=None, ge=Decimal("-100"), le=Decimal("1000"), max_digits=9, decimal_places=6
    )
    is_locked: bool = False
    lock_start_date: date | None = None
    lock_end_date: date | None = None
    notes: Notes | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_lock_dates(self) -> AccountCreate:
        _validate_lock_dates(self.lock_start_date, self.lock_end_date)
        return self


class AccountUpdate(BaseModel):
    name: Name120 | None = None
    account_type: AccountType | None = None
    opening_balance: Decimal | None = Field(default=None, max_digits=20, decimal_places=4)
    opening_balance_date: date | None = None
    currency: CurrencyCode | None = None
    interest_rate: Decimal | None = Field(
        default=None, ge=Decimal("-100"), le=Decimal("1000"), max_digits=9, decimal_places=6
    )
    is_locked: bool | None = None
    lock_start_date: date | None = None
    lock_end_date: date | None = None
    notes: Notes | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None


class AccountRead(ArchivedApiModel):
    account_id: int
    name: str
    account_type: AccountType
    opening_balance: Decimal
    opening_balance_date: date
    currency: str
    interest_rate: Decimal | None
    is_locked: bool
    lock_start_date: date | None
    lock_end_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CategoryCreate(BaseModel):
    name: Name120
    category_kind: CategoryKind
    parent_category_id: int | None = Field(default=None, gt=0)
    notes: Notes | None = None


class CategoryUpdate(BaseModel):
    name: Name120 | None = None
    category_kind: CategoryKind | None = None
    parent_category_id: int | None = Field(default=None, gt=0)
    notes: Notes | None = None


class CategoryRead(ArchivedApiModel):
    category_id: int
    parent_category_id: int | None
    name: str
    category_kind: CategoryKind
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CategoryLinkCreate(BaseModel):
    first_category_id: int = Field(gt=0)
    second_category_id: int = Field(gt=0)
    label: Name120 | None = None


class CategoryLinkRead(ApiModel):
    category_link_id: int
    lower_category_id: int
    higher_category_id: int
    label: str | None
    created_at: datetime
    updated_at: datetime


class ProviderCreate(BaseModel):
    name: Name160
    website: str | None = Field(default=None, max_length=512)
    notes: Notes | None = None


class ProviderUpdate(BaseModel):
    name: Name160 | None = None
    website: str | None = Field(default=None, max_length=512)
    notes: Notes | None = None


class ProviderRead(ArchivedApiModel):
    provider_id: int
    name: str
    website: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ProviderAliasCreate(BaseModel):
    alias: Alias


class ProviderAliasUpdate(BaseModel):
    alias: Alias


class ProviderAliasRead(ApiModel):
    provider_alias_id: int
    provider_id: int
    alias: str
    created_at: datetime
    updated_at: datetime


class ProviderLinkCreate(BaseModel):
    first_provider_id: int = Field(gt=0)
    second_provider_id: int = Field(gt=0)
    label: Name120 | None = None


class ProviderLinkRead(ApiModel):
    provider_link_id: int
    lower_provider_id: int
    higher_provider_id: int
    label: str | None
    created_at: datetime
    updated_at: datetime


class TagCreate(BaseModel):
    name: TagName
    color: HexColor | None = None


class TagUpdate(BaseModel):
    name: TagName | None = None
    color: HexColor | None = None


class TagRead(ArchivedApiModel):
    tag_id: int
    name: str
    color: str | None
    created_at: datetime
    updated_at: datetime


class SharingPartyCreate(BaseModel):
    name: Name120
    is_self: bool = False
    notes: Notes | None = None


class SharingPartyUpdate(BaseModel):
    name: Name120 | None = None
    is_self: bool | None = None
    notes: Notes | None = None


class SharingPartyRead(ArchivedApiModel):
    sharing_party_id: int
    name: str
    is_self: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


def _validate_lock_dates(start: date | None, end: date | None) -> None:
    if end is not None and start is None:
        raise ValueError("lock_end_date requires lock_start_date")
    if start is not None and end is not None and end < start:
        raise ValueError("lock_end_date must be on or after lock_start_date")
