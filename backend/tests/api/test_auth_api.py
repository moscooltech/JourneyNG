"""Auth API tests: register, login, refresh rotation, logout, reuse detection."""

from __future__ import annotations

import pytest

REGISTER_PAYLOAD = {
    "display_name": "John Doe",
    "email": "john@example.com",
    "phone": None,
    "password": "strong-pass-123",
}


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "john@example.com"
    assert body["access_token"]
    assert body["refresh_token"]
    assert "password_hash" not in body["user"]


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_register_weak_password(client):
    payload = {**REGISTER_PAYLOAD, "email": "weak@example.com", "password": "short"}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success_and_wrong_password(client):
    await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)

    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "john@example.com", "password": "strong-pass-123"},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/auth/login",
        json={"identifier": "john@example.com", "password": "wrong-password-1"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_refresh_rotation(client):
    register = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    old_refresh = register.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["refresh_token"] != old_refresh

    # Old (now revoked) token must not refresh again.
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_family(client):
    register = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    first = register.json()["refresh_token"]

    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert rotated.status_code == 200
    current = rotated.json()["refresh_token"]

    # Replaying the revoked first token revokes the whole family.
    replay = await client.post("/api/v1/auth/refresh", json={"refresh_token": first})
    assert replay.status_code == 401

    replay2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": current})
    assert replay2.status_code == 401  # family revoked


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_profile(client):
    register = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    token = register.json()["access_token"]
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["display_name"] == "John Doe"
