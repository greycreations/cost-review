from __future__ import annotations

import hmac
from collections.abc import Generator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.errors import ApiError
from app.models import Session, User
from app.security import hash_token, token_matches


@dataclass(frozen=True, slots=True)
class AuthContext:
    session: Session
    user: User


def get_runtime_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[DbSession]:
    with request.app.state.database.session() as db:
        yield db


DatabaseSession = Annotated[DbSession, Depends(get_db)]
RuntimeSettings = Annotated[Settings, Depends(get_runtime_settings)]


def get_auth_context(
    request: Request,
    db: DatabaseSession,
    settings: RuntimeSettings,
) -> AuthContext:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise ApiError(401, "authentication_required", "Authentication is required.")

    session = db.get(Session, hash_token(raw_token))
    now = datetime.now(UTC)
    if session is None or session.expires_at <= now:
        if session is not None:
            db.delete(session)
            db.commit()
        raise ApiError(401, "session_expired", "The session is missing or has expired.")

    user = db.get(User, session.user_id)
    if user is None:
        raise ApiError(401, "authentication_required", "Authentication is required.")
    session.last_seen_at = now
    return AuthContext(session=session, user=user)


Auth = Annotated[AuthContext, Depends(get_auth_context)]


def require_csrf(
    request: Request,
    auth: Auth,
    settings: RuntimeSettings,
) -> AuthContext:
    header_token = request.headers.get("X-CSRF-Token")
    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    if (
        not header_token
        or not cookie_token
        or not hmac.compare_digest(header_token, cookie_token)
        or not token_matches(header_token, auth.session.csrf_token_hash)
    ):
        raise ApiError(403, "csrf_failed", "The CSRF token is missing or invalid.")
    return auth


CsrfAuth = Annotated[AuthContext, Depends(require_csrf)]
