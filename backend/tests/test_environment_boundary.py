from __future__ import annotations

import pytest

from app.config import Settings
from app.database import Database, EnvironmentMismatchError, ensure_environment_identity


def test_persistent_environment_identity_rejects_wrong_runtime(
    settings: Settings,
) -> None:
    database = Database(settings)
    ensure_environment_identity(database, settings)
    wrong_environment = settings.model_copy(
        update={
            "app_environment": "production",
            "app_environment_label": "Production",
            "session_cookie_name": "cost_review_production_session",
            "csrf_cookie_name": "cost_review_production_csrf",
        }
    )

    with pytest.raises(EnvironmentMismatchError):
        ensure_environment_identity(database, wrong_environment)

    database.dispose()
