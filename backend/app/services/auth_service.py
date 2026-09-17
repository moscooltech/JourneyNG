"""Authentication service: register, login, refresh rotation, logout."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import get_settings
from app.core.errors import AppError, ConflictError, ErrorCode, UnauthenticatedError
from app.core.timeutils import ensure_utc
from app.models.profile import Profile
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.security.jwt import create_access_token
from app.security.password import hash_password, validate_password_strength, verify_password
from app.security.tokens import generate_token, hash_token


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _normalize_identifier(identifier: str) -> str:
    ident = identifier.strip().lower()
    if "@" in ident:
        return ident
    return (
        "".join(c for c in ident if c.isdigit() or c == "+")[1:] if ident.startswith("+") else ident
    )


async def register_user(db: AsyncSession, req: RegisterRequest) -> tuple[User, str, str]:
    """Returns (user, access_token, refresh_token)."""
    validate_password_strength(req.password)

    email = _normalize_email(req.email)
    existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(ErrorCode.EMAIL_TAKEN, "An account with this email exists.")

    user = User(
        email=email,
        phone=req.phone,
        password_hash=hash_password(req.password),
        auth_provider="password",
        status="ACTIVE",
    )
    db.add(user)
    await db.flush()
    db.add(Profile(user_id=user.id, display_name=req.display_name))
    await db.flush()

    access = create_access_token(str(user.id))
    refresh = await _issue_refresh_token(db, user.id)
    return user, access, refresh


async def login(db: AsyncSession, identifier: str, password: str) -> tuple[User, str, str]:
    email = _normalize_identifier(identifier)
    user = (
        await db.execute(
            select(User).options(selectinload(User.profile)).where(User.email == email)
        )
    ).scalar_one_or_none()
    if user is None or user.password_hash is None:
        raise UnauthenticatedError("Invalid credentials.", code=ErrorCode.INVALID_CREDENTIALS)
    if user.status == "DELETED":
        raise UnauthenticatedError("Account no longer available.")
    if user.status == "SUSPENDED":
        raise AppError(ErrorCode.ACCOUNT_SUSPENDED, "Account suspended.", 403)
    if not verify_password(user.password_hash, password):
        raise UnauthenticatedError("Invalid credentials.", code=ErrorCode.INVALID_CREDENTIALS)

    user.last_login_at = datetime.now(UTC)
    access = create_access_token(str(user.id))
    refresh = await _issue_refresh_token(db, user.id)
    return user, access, refresh


async def _issue_refresh_token(db: AsyncSession, user_id) -> str:
    settings = get_settings()
    raw = generate_token(32)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=settings.jwt_refresh_expires_days),
        )
    )
    await db.flush()
    return raw


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[User, str, str]:
    """Validates and rotates a refresh token. Reuse of a revoked token revokes family."""
    stored_hash = hash_token(raw_token)
    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == stored_hash))
    ).scalar_one_or_none()
    if rt is None:
        raise UnauthenticatedError("Invalid refresh token.")

    if rt.revoked_at is not None:
        # Token reuse detected: revoke all sessions for this user (defense in depth).
        # Commit explicitly — the raised error would otherwise roll this back.
        stmt = select(RefreshToken).where(RefreshToken.user_id == rt.user_id)
        for sibling in (await db.execute(stmt)).scalars():
            if sibling.revoked_at is None:
                sibling.revoked_at = datetime.now(UTC)
        await db.commit()
        raise UnauthenticatedError("Refresh token reuse detected; all sessions revoked.")

    if ensure_utc(rt.expires_at) < datetime.now(UTC):
        raise UnauthenticatedError("Refresh token expired.")

    rt.revoked_at = datetime.now(UTC)
    user = await db.get(User, rt.user_id)
    if user is None or user.status == "DELETED":
        raise UnauthenticatedError("Account no longer available.")

    access = create_access_token(str(user.id))
    new_raw = await _issue_refresh_token(db, user.id)
    return user, access, new_raw


async def logout(db: AsyncSession, raw_token: str) -> None:
    stored_hash = hash_token(raw_token)
    rt = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == stored_hash))
    ).scalar_one_or_none()
    if rt is not None and rt.revoked_at is None:
        rt.revoked_at = datetime.now(UTC)


async def revoke_all_sessions(db: AsyncSession, user_id) -> None:
    now = datetime.now(UTC)
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    for rt in (await db.execute(stmt)).scalars():
        rt.revoked_at = now
