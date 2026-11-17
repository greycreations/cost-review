from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import Settings, get_settings
from app.main import create_app
from app.services import HOUSEHOLD_DATA_TABLES


@pytest.fixture(scope="session")
def settings() -> Settings:
    runtime = get_settings()
    if runtime.app_environment != "test":
        raise RuntimeError("backend tests must run with APP_ENVIRONMENT=test")
    return runtime


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient]:
    app = create_app(settings)
    with TestClient(app) as test_client:
        clean_database(app.state.database)
        yield test_client
        clean_database(app.state.database)


@pytest.fixture
def registration_client(settings: Settings) -> Generator[TestClient]:
    """A client for an installation that has opted in to self-registration."""

    app = create_app(settings.model_copy(update={"allow_self_registration": True}))
    with TestClient(app) as test_client:
        clean_database(app.state.database)
        yield test_client
        clean_database(app.state.database)


def clean_database(database) -> None:
    tables = (*HOUSEHOLD_DATA_TABLES, "sessions", "app_settings", "users")
    with database.engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE")
        )
        connection.execute(text("UPDATE environment_metadata SET reset_generation = 0"))
