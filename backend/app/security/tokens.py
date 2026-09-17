"""Opaque token utilities.

Raw tokens exist only in memory/URLs; the database stores SHA-256 hashes.
Used for refresh tokens, invitation tokens and guest session tokens.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets


def generate_token(nbytes: int = 32) -> str:
    """Cryptographically secure URL-safe random token."""
    return secrets.token_urlsafe(nbytes)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    """Constant-time comparison."""
    return hmac.compare_digest(a, b)
