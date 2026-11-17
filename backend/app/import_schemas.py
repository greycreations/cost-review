from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.import_parsing import CSV_DELIMITERS, DATE_FORMATS
from app.ledger_schemas import Name120

ColumnName = str


class ImportMappingInput(BaseModel):
    date_column: ColumnName = Field(min_length=1, max_length=120)
    description_column: ColumnName = Field(min_length=1, max_length=120)
    amount_column: ColumnName | None = Field(default=None, max_length=120)
    debit_column: ColumnName | None = Field(default=None, max_length=120)
    credit_column: ColumnName | None = Field(default=None, max_length=120)
    posting_date_column: ColumnName | None = Field(default=None, max_length=120)
    currency_column: ColumnName | None = Field(default=None, max_length=120)
    reference_column: ColumnName | None = Field(default=None, max_length=120)
    date_format: str = "%Y-%m-%d"
    decimal_separator: Literal[",", "."] = ","
    amount_sign: Literal["as_is", "inverted"] = "as_is"
    delimiter: str | None = None
    header_row: int = Field(default=1, ge=1, le=100)

    @field_validator("date_format")
    @classmethod
    def known_date_format(cls, value: str) -> str:
        if value not in DATE_FORMATS:
            raise ValueError(f"date format must be one of {', '.join(DATE_FORMATS)}")
        return value

    @field_validator("delimiter")
    @classmethod
    def known_delimiter(cls, value: str | None) -> str | None:
        if value is not None and value not in CSV_DELIMITERS:
            raise ValueError("delimiter must be semicolon, comma, tab or pipe")
        return value

    @model_validator(mode="after")
    def amount_source(self) -> ImportMappingInput:
        if self.amount_column is None and self.debit_column is None and self.credit_column is None:
            raise ValueError("map an amount column or debit/credit columns")
        if self.amount_column is not None and (self.debit_column or self.credit_column):
            raise ValueError("use either one amount column or debit/credit columns, not both")
        return self


class ImportStageOptions(BaseModel):
    account_id: int = Field(gt=0)
    import_profile_id: int | None = Field(default=None, gt=0)
    mapping: ImportMappingInput | None = None
    save_profile_name: Name120 | None = None

    @model_validator(mode="after")
    def mapping_source(self) -> ImportStageOptions:
        if self.mapping is None and self.import_profile_id is None:
            raise ValueError("choose a saved import profile or provide a column mapping")
        return self


class ImportProfileSuggestion(BaseModel):
    import_profile_id: int
    name: str
    confidence: int


class PreviousImport(BaseModel):
    import_batch_id: int
    status: str
    created_at: datetime


class ImportPreviewRead(BaseModel):
    filename: str
    headers: list[str]
    sample_rows: list[dict[str, Any]]
    row_count: int
    delimiter: str | None
    suggested_mapping: dict[str, Any]
    profile_suggestions: list[ImportProfileSuggestion]
    previous_imports: list[PreviousImport]


class ImportProfileUpdate(BaseModel):
    name: Name120 | None = None
    default_account_id: int | None = Field(default=None, gt=0)


class ImportProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_profile_id: int
    name: str
    delimiter: str | None
    header_row: int
    date_column: str
    description_column: str
    amount_column: str | None
    debit_column: str | None
    credit_column: str | None
    posting_date_column: str | None
    currency_column: str | None
    reference_column: str | None
    date_format: str
    decimal_separator: str
    amount_sign: str
    default_account_id: int | None
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ImportBatchRead(BaseModel):
    import_batch_id: int
    import_profile_id: int | None
    account_id: int
    filename: str
    status: str
    row_count: int
    status_counts: dict[str, int]
    created_by_user_id: int | None
    created_at: datetime
    committed_at: datetime | None
    undone_at: datetime | None


class ImportRowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_row_id: int
    row_number: int
    raw: dict[str, Any]
    transaction_date: date | None
    posting_date: date | None
    description: str | None
    amount: Decimal | None
    currency: str | None
    reference: str | None
    category_id: int | None
    provider_id: int | None
    status: str
    errors: list[str]
    duplicate_transaction_id: int | None
    duplicate_confidence: int | None
    duplicate_reason: str | None
    transaction_id: int | None


class ImportRowPage(BaseModel):
    items: list[ImportRowRead]
    total: int
    limit: int
    offset: int


class ImportRowUpdate(BaseModel):
    transaction_date: date | None = None
    posting_date: date | None = None
    description: str | None = Field(default=None, min_length=1, max_length=240)
    amount: Decimal | None = Field(default=None, max_digits=20, decimal_places=4)
    category_id: int | None = Field(default=None, gt=0)
    provider_id: int | None = Field(default=None, gt=0)
    status: Literal["ready", "skipped"] | None = None


class ImportBulkUpdate(BaseModel):
    import_row_ids: list[int] = Field(min_length=1, max_length=5000)
    status: Literal["ready", "skipped"] | None = None
    category_id: int | None = Field(default=None, gt=0)
    provider_id: int | None = Field(default=None, gt=0)


class ImportUndoPreviewRead(BaseModel):
    import_batch_id: int
    transaction_count: int
    active_transaction_count: int
    expenses: Decimal
    income: Decimal
    edited_after_import_count: int
    linked_recovery_count: int
    can_undo: bool


class ImportUndoRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=64)
