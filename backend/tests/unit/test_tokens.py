"""Token/password security unit tests."""

from __future__ import annotations

import pytest

from app.core.errors import AppError
from app.security.jwt import create_access_token, decode_access_token
from app.security.password import hash_password, validate_password_strength, verify_password
from app.security.tokens import generate_token, hash_token, tokens_equal


class TestOpaqueTokens:
    def test_tokens_unique(self):
        assert generate_token() != generate_token()

    def test_hash_deterministic(self):
        raw = generate_token()
        assert hash_token(raw) == hash_token(raw)
        assert hash_token(raw) != hash_token(generate_token())

    def test_constant_time_compare(self):
        assert tokens_equal("abc", "abc")
        assert not tokens_equal("abc", "abd")


class TestJWT:
    def test_roundtrip(self):
        token = create_access_token("user-123")
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["typ"] == "access"

    def test_garbage_rejected(self):
        from app.core.errors import UnauthenticatedError

        with pytest.raises(UnauthenticatedError):
            decode_access_token("not.a.jwt")


class TestPasswords:
    def test_hash_verify_roundtrip(self):
        h = hash_password("correct-horse-9")
        assert verify_password(h, "correct-horse-9")
        assert not verify_password(h, "wrong-password-1")

    def test_hash_is_argon2id(self):
        assert hash_password("some-password-1").startswith("$argon2id$")

    def test_short_password_rejected(self):
        with pytest.raises(AppError):
            validate_password_strength("a1")

    def test_repeated_password_rejected(self):
        with pytest.raises(AppError):
            validate_password_strength("aaaaaaaaaaaa")

    def test_letters_only_rejected(self):
        with pytest.raises(AppError):
            validate_password_strength("onlylettershere")
