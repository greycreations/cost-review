from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.config import Settings, get_settings
from app.main import create_app


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


def clean_database(database) -> None:
    with database.engine.begin() as connection:
        connection.execute(
            text("TRUNCATE TABLE sessions, app_settings, users RESTART IDENTITY CASCADE")
        )
        connection.execute(text("UPDATE environment_metadata SET reset_generation = 0"))
