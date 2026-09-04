from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.errors import ApiError
from app.models import AppSettings, EnvironmentMetadata, Session, User
from app.schemas import SettingsInput, SettingsUpdate, SetupRequest
from app.security import (
    generate_token,
    hash_password,
    hash_token,
    normalize_username,
    verify_password,
)


@dataclass(frozen=True, slots=True)
class IssuedSession:
    model: Session
    raw_session_token: str
    raw_csrf_token: str


def get_environment_metadata(db: DbSession) -> EnvironmentMetadata:
    metadata = db.get(EnvironmentMetadata, 1)
    if metadata is None:
        raise RuntimeError("environment identity has not been initialized")
    return metadata


def setup_required(db: DbSession) -> bool:
    return (db.scalar(select(func.count(User.user_id))) or 0) == 0


def create_initial_user(db: DbSession, payload: SetupRequest) -> User:
    password_hash = hash_password(payload.password)
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": "cost-review-initial-setup"},
    )
    if not setup_required(db):
        raise ApiError(409, "setup_locked", "Initial setup has already been completed.")

    user = User(
        username=payload.username,
        normalized_username=normalize_username(payload.username),
        password_hash=password_hash,
    )
    user.settings = AppSettings(**settings_values(payload.settings))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: DbSession, username: str, password: str) -> User:
    user = db.scalar(
        select(User).where(User.normalized_username == normalize_username(username))
    )
    if user is None or not verify_password(user.password_hash, password):
        raise ApiError(401, "invalid_credentials", "Username or password is incorrect.")
    return user


def issue_session(db: DbSession, user: User, settings: Settings) -> IssuedSession:
    now = datetime.now(UTC)
    raw_session_token = generate_token()
    raw_csrf_token = generate_token()
    model = Session(
        session_token_hash=hash_token(raw_session_token),
        user_id=user.user_id,
        csrf_token_hash=hash_token(raw_csrf_token),
        expires_at=now + timedelta(hours=settings.session_ttl_hours),
        last_seen_at=now,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return IssuedSession(model, raw_session_token, raw_csrf_token)


def update_settings(db: DbSession, model: AppSettings, payload: SettingsUpdate) -> AppSettings:
    values = payload.model_dump(exclude_none=True, mode="json")
    for field_name, value in values.items():
        setattr(model, field_name, value)
    db.commit()
    db.refresh(model)
    return model


def reset_test_environment(
    db: DbSession,
    settings: Settings,
    current_session_hash: str,
) -> EnvironmentMetadata:
    if settings.app_environment != "test":
        raise ApiError(404, "not_found", "Resource not found.")

    metadata = get_environment_metadata(db)
    db.execute(
        text(
            "TRUNCATE TABLE audit_events, budget_providers, budget_accounts, budget_tags, "
            "budget_categories, budgets, analysis_group_providers, "
            "analysis_group_accounts, analysis_group_tags, analysis_group_categories, "
            "analysis_groups, "
            "account_snapshots, refund_links, reimbursement_links, "
            "transfer_links, transaction_split_tags, "
            "transaction_splits, "
            "transactions, "
            "category_links, provider_links, provider_aliases, "
            "accounts, categories, providers, tags, sharing_parties RESTART IDENTITY CASCADE"
        )
    )
    db.execute(delete(Session).where(Session.session_token_hash != current_session_hash))
    app_settings = db.scalar(select(AppSettings))
    if app_settings is not None:
        defaults = settings_values(SettingsInput())
        for field_name, value in defaults.items():
            setattr(app_settings, field_name, value)
    metadata.reset_generation += 1
    db.commit()
    db.refresh(metadata)
    return metadata


def settings_values(payload: SettingsInput) -> dict[str, str]:
    return payload.model_dump(mode="json")
