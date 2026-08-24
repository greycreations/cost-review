from __future__ import annotations

import os
from dataclasses import dataclass, field


def _cors_origins() -> tuple[str, ...]:
    raw_value = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:8080",
    )
    return tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Cost Review API"
    api_prefix: str = "/api/v1"
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///../data/costreview.db")
    )
    cors_origins: tuple[str, ...] = field(default_factory=_cors_origins)


settings = Settings()
