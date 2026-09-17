"""Authentication/authorization dependencies.

Identity sources, in priority order:
1. Bearer JWT (registered users)
2. Guest session token (X-Guest-Token header) — scoped to one journey

The backend NEVER trusts a client-supplied user_id or participant_id for
authorization decisions.
"""

from __future__ import annotations

import uuid as uuid_mod
from dataclasses import dataclass

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ErrorCode, ForbiddenError, UnauthenticatedError
from app.infrastructure.database import get_db
from app.models.guest_session import GuestSession
from app.models.user import User
from app.security.jwt import decode_access_token
from app.security.tokens import hash_token


@dataclass(frozen=True)
class Requester:
    """Resolved identity for a request: exactly one of user or guest session."""

    user: User | None
    guest_session: GuestSession | None
    ip: str

    @property
    def user_id(self) -> str | None:
        return str(self.user.id) if self.user else None

    @property
    def guest_session_id(self) -> str | None:
        return str(self.guest_session.id) if self.guest_session else None

    @property
    def display_name(self) -> str:
        if self.user and self.user.profile:
            return self.user.profile.display_name
        if self.guest_session:
            return self.guest_session.display_name
        return "Unknown"


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_requester(
    request: Request,
    x_guest_token: str | None = Header(default=None, alias="X-Guest-Token"),
    db: AsyncSession = Depends(get_db),
) -> Requester:
    authorization = request.headers.get("authorization", "")
    ip = _client_ip(request)

    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthenticatedError("Invalid token subject.")
        try:
            user_pk = uuid_mod.UUID(str(user_id))
        except ValueError as exc:
            raise UnauthenticatedError("Invalid token subject.") from exc
        user = (
            await db.execute(
                select(User).options(selectinload(User.profile)).where(User.id == user_pk)
            )
        ).scalar_one_or_none()
        if user is None or user.status == "DELETED":
            raise UnauthenticatedError("Account no longer available.")
        if user.status == "SUSPENDED":
            raise ForbiddenError("Account suspended.", code=ErrorCode.ACCOUNT_SUSPENDED)
        return Requester(user=user, guest_session=None, ip=ip)

    if x_guest_token:
        stmt = select(GuestSession).where(GuestSession.token_hash == hash_token(x_guest_token))
        session = (await db.execute(stmt)).scalar_one_or_none()
        if session is None or session.status not in ("ACTIVE", "COMPLETED"):
            raise UnauthenticatedError("Guest session invalid or revoked.")
        if session.is_expired:
            raise UnauthenticatedError("Guest session expired.")
        return Requester(user=None, guest_session=session, ip=ip)

    raise UnauthenticatedError()
