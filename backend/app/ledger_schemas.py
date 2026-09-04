from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.models import (
    AccountType,
    AdjustmentDirection,
    CategoryKind,
    FxRateStatus,
    LifecycleStatus,
    TransactionKind,
    TransactionSource,
    TransferPurpose,
)

Name120 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Name160 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)]
Alias = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
TagName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)
]


class ManualTransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class AnalysisPerspective(StrEnum):
    TOTAL = "total"
    MY_SHARE = "my_share"


class LedgerTransactionKind(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"
    REFUND = "refund"
    REIMBURSEMENT = "reimbursement"
    ADJUSTMENT = "adjustment"


class ComparisonMode(StrEnum):
    NONE = "none"
    PREVIOUS_PERIOD = "previous_period"
    PREVIOUS_YEAR = "previous_year"


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


class AccountSnapshotCreate(BaseModel):
    valuation_date: date
    reported_balance: Decimal = Field(max_digits=20, decimal_places=4)
    converted_balance: Decimal | None = Field(default=None, max_digits=20, decimal_places=4)
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=10)
    notes: Notes | None = None


class AccountSnapshotUpdate(BaseModel):
    valuation_date: date | None = None
    reported_balance: Decimal | None = Field(default=None, max_digits=20, decimal_places=4)
    converted_balance: Decimal | None = Field(default=None, max_digits=20, decimal_places=4)
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=10)
    notes: Notes | None = None


class AccountSnapshotRead(ArchivedApiModel):
    account_snapshot_id: int
    account_id: int
    valuation_date: date
    reported_balance: Decimal
    currency: str
    converted_balance: Decimal | None
    base_currency: str
    fx_rate: Decimal | None
    fx_rate_status: FxRateStatus
    calculated_balance: Decimal | None
    difference: Decimal | None
    calculation_status: str
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


class TagMergeRequest(BaseModel):
    target_tag_id: int = Field(gt=0)
    confirmation: Literal["MERGE TAG"]


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


class ShareAllocationInput(BaseModel):
    sharing_party_id: int = Field(gt=0)
    percentage: Decimal = Field(gt=0, le=100, max_digits=7, decimal_places=4)


class ShareAllocationRead(BaseModel):
    sharing_party_id: int
    percentage: Decimal
    is_self: bool


class TransactionSplitInput(BaseModel):
    original_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    category_id: int | None = Field(default=None, gt=0)
    tag_ids: list[int] = Field(default_factory=list, max_length=50)
    is_base_cost: bool = False
    memo: str | None = Field(default=None, max_length=240)
    sharing_allocations: list[ShareAllocationInput] = Field(default_factory=list, max_length=50)

    @field_validator("tag_ids")
    @classmethod
    def unique_tag_ids(cls, value: list[int]) -> list[int]:
        if any(tag_id <= 0 for tag_id in value):
            raise ValueError("tag identifiers must be positive")
        if len(set(value)) != len(value):
            raise ValueError("tag identifiers must be unique")
        return value

    @field_validator("sharing_allocations")
    @classmethod
    def valid_sharing_allocations(
        cls, value: list[ShareAllocationInput]
    ) -> list[ShareAllocationInput]:
        identifiers = [item.sharing_party_id for item in value]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("sharing party identifiers must be unique")
        if value and sum((item.percentage for item in value), Decimal("0")) != Decimal("100"):
            raise ValueError("sharing allocation percentages must total 100")
        return value


class TransactionSplitRead(ApiModel):
    transaction_split_id: int
    original_amount: Decimal
    converted_amount: Decimal | None
    category_id: int | None
    tag_ids: list[int]
    is_base_cost: bool
    memo: str | None
    sharing_allocations: list[ShareAllocationRead]


class TransactionCreate(BaseModel):
    account_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    transaction_kind: ManualTransactionKind
    transaction_date: date
    posting_date: date
    description: Description
    original_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    original_currency: CurrencyCode
    converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=10)
    category_id: int | None = Field(default=None, gt=0)
    tag_ids: list[int] = Field(default_factory=list, max_length=50)
    is_base_cost: bool = False
    sharing_allocations: list[ShareAllocationInput] = Field(default_factory=list, max_length=50)
    splits: list[TransactionSplitInput] | None = Field(
        default=None, min_length=2, max_length=100
    )
    source_reference: str | None = Field(default=None, max_length=240)
    notes: Notes | None = None

    @field_validator("original_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("tag_ids")
    @classmethod
    def unique_tag_ids(cls, value: list[int]) -> list[int]:
        if any(tag_id <= 0 for tag_id in value):
            raise ValueError("tag identifiers must be positive")
        if len(set(value)) != len(value):
            raise ValueError("tag identifiers must be unique")
        return value

    @field_validator("sharing_allocations")
    @classmethod
    def valid_sharing_allocations(
        cls, value: list[ShareAllocationInput]
    ) -> list[ShareAllocationInput]:
        return _validate_sharing_allocations(value)

    @model_validator(mode="after")
    def validate_splits(self) -> TransactionCreate:
        if self.splits is None:
            return self
        if (
            self.category_id is not None
            or self.tag_ids
            or self.is_base_cost
            or self.sharing_allocations
        ):
            raise ValueError("split transactions must keep classification on their splits")
        split_total = sum((split.original_amount for split in self.splits), Decimal("0"))
        if split_total.quantize(Decimal("0.0001")) != self.original_amount.quantize(
            Decimal("0.0001")
        ):
            raise ValueError("split amounts must equal the transaction amount")
        return self


class TransactionUpdate(BaseModel):
    account_id: int | None = Field(default=None, gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    transaction_kind: ManualTransactionKind | None = None
    transaction_date: date | None = None
    posting_date: date | None = None
    description: Description | None = None
    original_amount: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=4)
    original_currency: CurrencyCode | None = None
    converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=10)
    category_id: int | None = Field(default=None, gt=0)
    tag_ids: list[int] | None = Field(default=None, max_length=50)
    is_base_cost: bool | None = None
    sharing_allocations: list[ShareAllocationInput] | None = Field(default=None, max_length=50)
    splits: list[TransactionSplitInput] | None = Field(
        default=None, min_length=2, max_length=100
    )
    source_reference: str | None = Field(default=None, max_length=240)
    notes: Notes | None = None

    @field_validator("original_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("tag_ids")
    @classmethod
    def unique_tag_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if any(tag_id <= 0 for tag_id in value):
            raise ValueError("tag identifiers must be positive")
        if len(set(value)) != len(value):
            raise ValueError("tag identifiers must be unique")
        return value

    @field_validator("sharing_allocations")
    @classmethod
    def valid_sharing_allocations(
        cls, value: list[ShareAllocationInput] | None
    ) -> list[ShareAllocationInput] | None:
        return _validate_sharing_allocations(value) if value is not None else None


class TransactionRead(ArchivedApiModel):
    transaction_id: int
    account_id: int
    provider_id: int | None
    transaction_kind: TransactionKind
    transaction_date: date
    posting_date: date
    description: str
    original_amount: Decimal
    original_currency: str
    converted_amount: Decimal | None
    base_currency: str
    fx_rate: Decimal | None
    fx_rate_status: FxRateStatus
    source_type: TransactionSource
    source_reference: str | None
    notes: str | None
    adjustment_direction: AdjustmentDirection | None
    category_id: int | None
    tag_ids: list[int]
    is_base_cost: bool
    is_split: bool
    splits: list[TransactionSplitRead]
    sharing_allocations: list[ShareAllocationRead]
    linked_expense_id: int | None = None
    created_at: datetime
    updated_at: datetime


class BalanceAdjustmentCreate(BaseModel):
    confirmation: str


class AuditEventRead(ApiModel):
    audit_event_id: int
    entity_type: str
    entity_id: int | None
    action: str
    change_source: str
    changes: dict[str, object]
    created_at: datetime


class RecycleBinItemRead(BaseModel):
    entity_type: str
    entity_id: int
    label: str
    archived_at: datetime
    restore_path: str


class RecoveryCreate(BaseModel):
    account_id: int = Field(gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    transaction_date: date
    posting_date: date
    description: Description
    original_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    original_currency: CurrencyCode
    converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    fx_rate: Decimal | None = Field(default=None, gt=0, max_digits=20, decimal_places=10)
    source_reference: str | None = Field(default=None, max_length=240)
    notes: Notes | None = None

    @field_validator("original_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class TransferCreate(BaseModel):
    source_account_id: int = Field(gt=0)
    destination_account_id: int = Field(gt=0)
    purpose: TransferPurpose = TransferPurpose.INTERNAL
    transaction_date: date
    source_posting_date: date
    destination_posting_date: date
    description: Description
    source_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    destination_amount: Decimal = Field(gt=0, max_digits=20, decimal_places=4)
    source_converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    source_fx_rate: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=10
    )
    destination_converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    destination_fx_rate: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=10
    )
    source_reference: str | None = Field(default=None, max_length=240)
    notes: Notes | None = None

    @model_validator(mode="after")
    def accounts_must_differ(self) -> TransferCreate:
        if self.source_account_id == self.destination_account_id:
            raise ValueError("source and destination accounts must differ")
        return self


class TransferUpdate(BaseModel):
    source_account_id: int | None = Field(default=None, gt=0)
    destination_account_id: int | None = Field(default=None, gt=0)
    purpose: TransferPurpose | None = None
    transaction_date: date | None = None
    source_posting_date: date | None = None
    destination_posting_date: date | None = None
    description: Description | None = None
    source_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    destination_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    source_converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    source_fx_rate: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=10
    )
    destination_converted_amount: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=4
    )
    destination_fx_rate: Decimal | None = Field(
        default=None, gt=0, max_digits=20, decimal_places=10
    )
    source_reference: str | None = Field(default=None, max_length=240)
    notes: Notes | None = None


class TransferRead(ArchivedApiModel):
    transfer_link_id: int
    source_account_id: int
    destination_account_id: int
    purpose: TransferPurpose
    transaction_date: date
    source_posting_date: date
    destination_posting_date: date
    description: str
    source_amount: Decimal
    source_currency: str
    source_converted_amount: Decimal | None
    source_fx_rate: Decimal | None
    source_fx_rate_status: FxRateStatus
    destination_amount: Decimal
    destination_currency: str
    destination_converted_amount: Decimal | None
    destination_fx_rate: Decimal | None
    destination_fx_rate_status: FxRateStatus
    base_currency: str
    source_reference: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LedgerSummaryRead(BaseModel):
    date_from: date
    date_to: date
    base_currency: str
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal
    transaction_count: int
    missing_fx_count: int
    perspective: AnalysisPerspective


class LedgerTrendPointRead(BaseModel):
    date: date
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal


class LedgerCategoryBreakdownRead(BaseModel):
    category_id: int | None
    category_name: str | None
    amount: Decimal
    transaction_count: int


class LedgerAnalysisRead(BaseModel):
    date_from: date
    date_to: date
    base_currency: str
    daily: list[LedgerTrendPointRead]
    expense_categories: list[LedgerCategoryBreakdownRead]
    comparison: LedgerComparisonRead | None = None
    perspective: AnalysisPerspective


class LedgerComparisonRead(BaseModel):
    mode: ComparisonMode
    date_from: date
    date_to: date
    income: Decimal
    expenses: Decimal
    net_cash_flow: Decimal
    daily: list[LedgerTrendPointRead]
    expense_categories: list[LedgerCategoryBreakdownRead]


def _validate_lock_dates(start: date | None, end: date | None) -> None:
    if end is not None and start is None:
        raise ValueError("lock_end_date requires lock_start_date")
    if start is not None and end is not None and end < start:
        raise ValueError("lock_end_date must be on or after lock_start_date")


def _validate_sharing_allocations(
    value: list[ShareAllocationInput],
) -> list[ShareAllocationInput]:
    identifiers = [item.sharing_party_id for item in value]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("sharing party identifiers must be unique")
    if value and sum((item.percentage for item in value), Decimal("0")) != Decimal("100"):
        raise ValueError("sharing allocation percentages must total 100")
    return value
