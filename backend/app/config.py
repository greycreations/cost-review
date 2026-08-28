from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL

EnvironmentKind = Literal["production", "test"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Cost Review API"
    api_prefix: str = "/api/v1"
    app_environment: EnvironmentKind = "production"
    app_environment_label: str = "Production"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "cost_review"
    db_user: str = "cost_review"
    db_password: str = Field(min_length=1)

    session_cookie_name: str = "cost_review_production_session"
    csrf_cookie_name: str = "cost_review_production_csrf"
    cookie_secure: bool = True
    session_ttl_hours: int = Field(default=12, ge=1, le=720)

    app_allowed_origins: str = "http://localhost:8080"
    app_allowed_hosts: str = "localhost,127.0.0.1"
    app_trusted_proxy_ips: str = "127.0.0.1"

    attachment_root: Path = Path("/app/storage/attachments")
    backup_root: Path = Path("/app/storage/backups")

    @field_validator("session_cookie_name", "csrf_cookie_name")
    @classmethod
    def validate_cookie_name(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("cookie names must be non-empty and contain no whitespace")
        return value

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )

    @property
    def allowed_origins(self) -> tuple[str, ...]:
        return self._csv(self.app_allowed_origins)

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        return self._csv(self.app_allowed_hosts)

    @property
    def trusted_proxy_ips(self) -> tuple[str, ...]:
        return self._csv(self.app_trusted_proxy_ips)

    @staticmethod
    def _csv(raw_value: str) -> tuple[str, ...]:
        return tuple(item.strip() for item in raw_value.split(",") if item.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
