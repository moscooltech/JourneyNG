"""JWT access tokens.

Short-lived HS256 tokens carrying minimal claims (sub, typ, iat, exp, jti).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config.settings import get_settings
from app.core.errors import UnauthenticatedError

ISSUER = "journey-sharing"


def _secret() -> str:
    return get_settings().effective_jwt_secret


def create_access_token(user_id: str, extra_claims: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "iss": ISSUER,
        "sub": user_id,
        "typ": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_expires_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _secret(), algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[settings.jwt_algorithm],
            issuer=ISSUER,
            options={"require": ["exp", "sub", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthenticatedError("Access token expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthenticatedError("Invalid access token.") from exc
    if payload.get("typ") != "access":
        raise UnauthenticatedError("Invalid token type.")
    return payload
