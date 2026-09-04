from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.models import DateFormat, Language, NumberFormat, WeekStart

Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=64)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=1024)]
CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
RegionCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=16)]


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EnvironmentRead(BaseModel):
    environment: str
    label: str
    data_plane_id: UUID
    reset_generation: int


class HealthRead(EnvironmentRead):
    status: str
    database: str


class SetupStatusRead(EnvironmentRead):
    setup_required: bool


class SettingsInput(BaseModel):
    language: Language = Language.SWEDISH
    region: RegionCode = "SE"
    base_currency: CurrencyCode = "SEK"
    timezone: str = Field(default="Europe/Stockholm", min_length=1, max_length=64)
    date_format: DateFormat = DateFormat.ISO
    number_format: NumberFormat = NumberFormat.SPACE_COMMA
    week_start: WeekStart = WeekStart.MONDAY

    @field_validator("base_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return value


class SettingsUpdate(BaseModel):
    language: Language | None = None
    region: RegionCode | None = None
    base_currency: CurrencyCode | None = None
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    date_format: DateFormat | None = None
    number_format: NumberFormat | None = None
    week_start: WeekStart | None = None

    @field_validator("base_currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.strip().upper() if value is not None else None

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("timezone must be a valid IANA timezone") from error
        return value


class AppSettingsRead(ApiModel):
    language: Language
    region: str
    base_currency: str
    timezone: str
    date_format: DateFormat
    number_format: NumberFormat
    week_start: WeekStart


class SetupRequest(BaseModel):
    username: Username
    password: Password
    settings: SettingsInput


class LoginRequest(BaseModel):
    username: Username
    password: str = Field(min_length=1, max_length=1024)


class SessionRead(BaseModel):
    username: str
    environment: str
    environment_label: str
    data_plane_id: UUID
    reset_generation: int
    expires_at: datetime
    settings: AppSettingsRead


class TestResetRequest(BaseModel):
    confirmation: str


class TestResetRead(BaseModel):
    environment: str
    data_plane_id: UUID
    reset_generation: int
    message: str


class BackupRead(BaseModel):
    filename: str
    environment: str
    kind: str
    created_at: datetime
    size_bytes: int


class BackupValidationRead(BaseModel):
    filename: str
    environment: str
    data_plane_id: UUID
    created_at: datetime
    schema_revision: str
    file_count: int
    valid: bool


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, object]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
