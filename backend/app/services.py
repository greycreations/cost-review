from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.errors import ApiError
from app.models import AppSettings, AuditEvent, EnvironmentMetadata, Session, User, UserRole
from app.schemas import (
    PasswordChangeRequest,
    SettingsInput,
    SettingsUpdate,
    SetupRequest,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.security import (
    generate_token,
    hash_password,
    hash_token,
    normalize_username,
    verify_password,
)

# Every table holding household data, in an order that TRUNCATE ... CASCADE
# accepts. The Demo/Test reset and the test suite share this list so a new table
# cannot be forgotten by one of them.
HOUSEHOLD_DATA_TABLES = (
    "audit_events",
    "recurring_occurrences",
    "recurring_versions",
    "recurring_definitions",
    "import_rows",
    "import_batches",
    "import_profiles",
    "investment_positions",
    "investment_portfolio_settings",
    "budget_providers",
    "budget_accounts",
    "budget_tags",
    "budget_categories",
    "budgets",
    "analysis_group_providers",
    "analysis_group_accounts",
    "analysis_group_tags",
    "analysis_group_categories",
    "analysis_groups",
    "account_snapshots",
    "refund_links",
    "reimbursement_links",
    "transfer_links",
    "transaction_split_tags",
    "transaction_split_shares",
    "transaction_splits",
    "transactions",
    "category_links",
    "provider_links",
    "provider_aliases",
    "accounts",
    "categories",
    "providers",
    "tags",
    "sharing_parties",
)

LOGIN_MAX_FAILURES = 5
LOGIN_LOCKOUT = timedelta(minutes=15)
DUMMY_PASSWORD_HASH = hash_password("cost-review-timing-equalizer")


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
        role=UserRole.OWNER,
    )
    user.settings = AppSettings(**settings_values(payload.settings))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_user_account(
    db: DbSession,
    payload: UserCreateRequest,
    *,
    actor_user_id: int | None,
    allow_role: bool,
) -> User:
    normalized_username = normalize_username(payload.username)
    password_hash = hash_password(payload.password)
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": f"cost-review-user:{normalized_username}"},
    )
    if db.scalar(select(User.user_id).where(User.normalized_username == normalized_username)):
        raise ApiError(409, "username_taken", "That username is already in use.")

    user = User(
        username=payload.username,
        normalized_username=normalized_username,
        password_hash=password_hash,
        role=payload.role if allow_role else UserRole.MEMBER,
    )
    user.settings = AppSettings(**settings_values(payload.settings))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as error:
        db.rollback()
        raise ApiError(409, "username_taken", "That username is already in use.") from error
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.user_id,
            action="created",
            change_source="user",
            actor_user_id=actor_user_id,
            changes={
                "actor_user_id": actor_user_id,
                "username": user.username,
                "role": user.role,
            },
        )
    )
    db.commit()
    db.refresh(user)
    return user


def list_users(db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.username, User.user_id)))


def update_user_account(
    db: DbSession,
    user: User,
    payload: UserUpdateRequest,
    *,
    actor_user_id: int,
) -> User:
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": "cost-review-user-administration"},
    )
    changes: dict[str, object] = {"actor_user_id": actor_user_id}
    if payload.username is not None and payload.username != user.username:
        normalized_username = normalize_username(payload.username)
        conflicting_id = db.scalar(
            select(User.user_id).where(
                User.normalized_username == normalized_username,
                User.user_id != user.user_id,
            )
        )
        if conflicting_id is not None:
            raise ApiError(409, "username_taken", "That username is already in use.")
        changes["username"] = {"from": user.username, "to": payload.username}
        user.username = payload.username
        user.normalized_username = normalized_username
    if payload.role is not None and payload.role != user.role:
        if user.is_owner and payload.role != UserRole.OWNER and _owner_count(db) <= 1:
            raise ApiError(
                409, "last_owner_required", "The household must keep at least one owner."
            )
        changes["role"] = {"from": user.role, "to": str(payload.role)}
        user.role = payload.role
    if len(changes) == 1:
        return user
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.user_id,
            action="updated",
            change_source="user",
            actor_user_id=actor_user_id,
            changes=changes,
        )
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise ApiError(409, "username_taken", "That username is already in use.") from error
    db.refresh(user)
    return user


def change_password(
    db: DbSession,
    user: User,
    payload: PasswordChangeRequest,
    *,
    current_session_hash: str,
) -> None:
    if not verify_password(user.password_hash, payload.current_password):
        raise ApiError(401, "invalid_current_password", "The current password is incorrect.")
    if verify_password(user.password_hash, payload.new_password):
        raise ApiError(422, "password_unchanged", "Choose a new password that is different.")
    user.password_hash = hash_password(payload.new_password)
    revoked = db.execute(
        delete(Session).where(
            Session.user_id == user.user_id,
            Session.session_token_hash != current_session_hash,
        )
    ).rowcount
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.user_id,
            action="password_changed",
            change_source="user",
            actor_user_id=user.user_id,
            changes={"actor_user_id": user.user_id, "other_sessions_revoked": revoked or 0},
        )
    )
    db.commit()


def reset_user_password(
    db: DbSession,
    user: User,
    new_password: str,
    *,
    actor_user_id: int,
) -> None:
    if user.user_id == actor_user_id:
        raise ApiError(
            422,
            "use_password_change",
            "Use the password change form for your own account.",
        )
    user.password_hash = hash_password(new_password)
    revoked = db.execute(delete(Session).where(Session.user_id == user.user_id)).rowcount
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user.user_id,
            action="password_reset",
            change_source="user",
            actor_user_id=actor_user_id,
            changes={"actor_user_id": actor_user_id, "sessions_revoked": revoked or 0},
        )
    )
    db.commit()


def delete_user_account(
    db: DbSession,
    user: User,
    *,
    actor_user_id: int,
    confirmation: str,
) -> None:
    if user.user_id == actor_user_id:
        raise ApiError(422, "cannot_delete_self", "You cannot delete your active account.")
    if confirmation != f"DELETE {user.username}":
        raise ApiError(422, "confirmation_mismatch", f"Type DELETE {user.username} exactly.")
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_name))"),
        {"lock_name": "cost-review-user-administration"},
    )
    if user.is_owner and _owner_count(db) <= 1:
        raise ApiError(409, "last_owner_required", "The household must keep at least one owner.")
    user_id = user.user_id
    username = user.username
    role = user.role
    db.delete(user)
    db.flush()
    db.add(
        AuditEvent(
            entity_type="user",
            entity_id=user_id,
            action="deleted",
            change_source="user",
            actor_user_id=actor_user_id,
            changes={
                "actor_user_id": actor_user_id,
                "username": username,
                "role": role,
            },
        )
    )
    db.commit()


def _owner_count(db: DbSession) -> int:
    return db.scalar(select(func.count(User.user_id)).where(User.role == UserRole.OWNER)) or 0


def authenticate_user(
    db: DbSession,
    username: str,
    password: str,
    *,
    max_failures: int = LOGIN_MAX_FAILURES,
    lockout: timedelta = LOGIN_LOCKOUT,
) -> User:
    """Verify credentials with uniform cost and a per-account lockout.

    An unknown username still costs one Argon2 verification, so response time
    does not reveal which accounts exist. After ``max_failures`` consecutive
    failures an account is locked for ``lockout``; a locked account is rejected
    before its password is checked.
    """

    user = db.scalar(
        select(User)
        .where(User.normalized_username == normalize_username(username))
        .with_for_update()
    )
    if user is None:
        verify_password(DUMMY_PASSWORD_HASH, password)
        raise ApiError(401, "invalid_credentials", "Username or password is incorrect.")

    now = datetime.now(UTC)
    if user.locked_until is not None and user.locked_until > now:
        db.rollback()
        raise ApiError(
            429,
            "account_temporarily_locked",
            "Too many failed sign-in attempts. Try again later.",
            [{"retry_after_seconds": int((user.locked_until - now).total_seconds()) + 1}],
        )

    if not verify_password(user.password_hash, password):
        user.failed_login_count += 1
        if user.failed_login_count >= max_failures:
            user.locked_until = now + lockout
            user.failed_login_count = 0
        db.commit()
        raise ApiError(401, "invalid_credentials", "Username or password is incorrect.")

    if user.failed_login_count or user.locked_until is not None:
        user.failed_login_count = 0
        user.locked_until = None
        db.commit()
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
        text(f"TRUNCATE TABLE {', '.join(HOUSEHOLD_DATA_TABLES)} RESTART IDENTITY CASCADE")
    )
    db.execute(delete(Session).where(Session.session_token_hash != current_session_hash))
    defaults = settings_values(SettingsInput())
    for app_settings in db.scalars(select(AppSettings)):
        for field_name, value in defaults.items():
            setattr(app_settings, field_name, value)
    metadata.reset_generation += 1
    db.commit()
    db.refresh(metadata)
    return metadata


def settings_values(payload: SettingsInput) -> dict[str, str]:
    return payload.model_dump(mode="json")
