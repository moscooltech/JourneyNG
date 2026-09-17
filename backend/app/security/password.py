"""Password hashing (Argon2id) and strength validation."""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.errors import AppError, ErrorCode

_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MiB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

_MIN_LENGTH = 10
_TOO_SIMPLE = re.compile(r"^(.)\1+$")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, ValueError):
        # Corrupt/legacy hash: treat as verification failure, not an error.
        return False


def validate_password_strength(password: str) -> None:
    """Raises AppError(WEAK_PASSWORD) when the password is unusable."""
    if len(password) < _MIN_LENGTH:
        raise AppError(
            ErrorCode.WEAK_PASSWORD,
            f"Password must be at least {_MIN_LENGTH} characters.",
            422,
        )
    if _TOO_SIMPLE.match(password):
        raise AppError(ErrorCode.WEAK_PASSWORD, "Password is too simple.", 422)
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AppError(
            ErrorCode.WEAK_PASSWORD,
            "Password must contain letters and numbers.",
            422,
        )
