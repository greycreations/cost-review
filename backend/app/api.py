from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Response
from sqlalchemy import select, text

from app.config import Settings
from app.dependencies import Auth, CsrfAuth, DatabaseSession, RuntimeSettings
from app.errors import ApiError
from app.models import AppSettings, EnvironmentMetadata, User
from app.schemas import (
    AppSettingsRead,
    EnvironmentRead,
    HealthRead,
    LoginRequest,
    SessionRead,
    SettingsUpdate,
    SetupRequest,
    SetupStatusRead,
    TestResetRead,
    TestResetRequest,
)
from app.services import (
    IssuedSession,
    authenticate_user,
    create_initial_user,
    get_environment_metadata,
    issue_session,
    reset_test_environment,
    setup_required,
    update_settings,
)

router = APIRouter()
test_router = APIRouter(prefix="/test", tags=["test-environment"])


@router.get("/health", response_model=HealthRead, tags=["system"])
def health(db: DatabaseSession, settings: RuntimeSettings) -> HealthRead:
    db.execute(text("SELECT 1"))
    metadata = get_environment_metadata(db)
    return HealthRead(
        status="ok",
        database="reachable",
        **environment_values(metadata, settings),
    )


@router.get("/environment", response_model=EnvironmentRead, tags=["system"])
def environment(db: DatabaseSession, settings: RuntimeSettings) -> EnvironmentRead:
    return EnvironmentRead(**environment_values(get_environment_metadata(db), settings))


@router.get("/setup/status", response_model=SetupStatusRead, tags=["setup"])
def setup_status(db: DatabaseSession, settings: RuntimeSettings) -> SetupStatusRead:
    metadata = get_environment_metadata(db)
    return SetupStatusRead(
        setup_required=setup_required(db),
        **environment_values(metadata, settings),
    )


@router.post("/setup", response_model=SessionRead, status_code=201, tags=["setup"])
def setup(
    payload: SetupRequest,
    response: Response,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> SessionRead:
    user = create_initial_user(db, payload)
    issued = issue_session(db, user, settings)
    set_session_cookies(response, issued, settings)
    return session_read(db, user, issued.model.expires_at, settings)


@router.post("/auth/login", response_model=SessionRead, tags=["authentication"])
def login(
    payload: LoginRequest,
    response: Response,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> SessionRead:
    user = authenticate_user(db, payload.username, payload.password)
    issued = issue_session(db, user, settings)
    set_session_cookies(response, issued, settings)
    return session_read(db, user, issued.model.expires_at, settings)


@router.get("/auth/session", response_model=SessionRead, tags=["authentication"])
def current_session(
    auth: Auth,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> SessionRead:
    return session_read(db, auth.user, auth.session.expires_at, settings)


@router.post("/auth/logout", status_code=204, tags=["authentication"])
def logout(
    response: Response,
    auth: CsrfAuth,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> Response:
    db.delete(auth.session)
    db.commit()
    clear_session_cookies(response, settings)
    response.status_code = 204
    return response


@router.get("/settings", response_model=AppSettingsRead, tags=["settings"])
def read_settings(auth: Auth) -> AppSettingsRead:
    return AppSettingsRead.model_validate(auth.user.settings)


@router.patch("/settings", response_model=AppSettingsRead, tags=["settings"])
def patch_settings(
    payload: SettingsUpdate,
    auth: CsrfAuth,
    db: DatabaseSession,
) -> AppSettingsRead:
    model = update_settings(db, auth.user.settings, payload)
    return AppSettingsRead.model_validate(model)


@test_router.post("/reset", response_model=TestResetRead)
def reset_test(
    payload: TestResetRequest,
    auth: CsrfAuth,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> TestResetRead:
    if payload.confirmation != "DELETE ALL TEST DATA":
        raise ApiError(
            422,
            "confirmation_mismatch",
            "Type DELETE ALL TEST DATA exactly to confirm the reset.",
        )
    metadata = reset_test_environment(
        db,
        settings,
        current_session_hash=auth.session.session_token_hash,
    )
    return TestResetRead(
        environment=metadata.environment,
        data_plane_id=metadata.data_plane_id,
        reset_generation=metadata.reset_generation,
        message="Demo/Test application data was reset. Production was not accessible.",
    )


def environment_values(metadata: EnvironmentMetadata, settings: Settings) -> dict[str, object]:
    return {
        "environment": metadata.environment,
        "label": settings.app_environment_label,
        "data_plane_id": metadata.data_plane_id,
        "reset_generation": metadata.reset_generation,
    }


def session_read(
    db: DatabaseSession,
    user: User,
    expires_at: datetime,
    settings: Settings,
) -> SessionRead:
    app_settings = db.scalar(select(AppSettings).where(AppSettings.user_id == user.user_id))
    if app_settings is None:
        raise RuntimeError("authenticated user has no application settings")
    metadata = get_environment_metadata(db)
    return SessionRead(
        username=user.username,
        environment=metadata.environment,
        environment_label=settings.app_environment_label,
        data_plane_id=metadata.data_plane_id,
        reset_generation=metadata.reset_generation,
        expires_at=expires_at,
        settings=AppSettingsRead.model_validate(app_settings),
    )


def set_session_cookies(response: Response, issued: IssuedSession, settings: Settings) -> None:
    max_age = max(1, int((issued.model.expires_at - datetime.now(UTC)).total_seconds()))
    response.set_cookie(
        key=settings.session_cookie_name,
        value=issued.raw_session_token,
        max_age=max_age,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="strict",
        path="/",
    )
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=issued.raw_csrf_token,
        max_age=max_age,
        secure=settings.cookie_secure,
        httponly=False,
        samesite="strict",
        path="/",
    )


def clear_session_cookies(response: Response, settings: Settings) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/", secure=settings.cookie_secure)
    response.delete_cookie(settings.csrf_cookie_name, path="/", secure=settings.cookie_secure)
