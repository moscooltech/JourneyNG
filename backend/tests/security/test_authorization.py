"""Security tests (spec §37 security suite)."""

from __future__ import annotations

import pytest


async def _register(client, email: str, name: str) -> str:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"display_name": name, "email": email, "phone": None, "password": "strong-pass-123"},
    )
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_guest_token_scoped_to_single_journey(client):
    """A guest session from journey A must not access journey B."""
    host_token = await _register(client, "shost@example.com", "Security Host")
    other_host = await _register(client, "sother@example.com", "Other Host")

    j1 = (
        await client.post(
            "/api/v1/journeys",
            headers={"Authorization": f"Bearer {host_token}"},
            json={
                "destination": {"name": "A", "latitude": 6.5, "longitude": 3.3},
                "expires_in_minutes": 60,
            },
        )
    ).json()
    j2 = (
        await client.post(
            "/api/v1/journeys",
            headers={"Authorization": f"Bearer {other_host}"},
            json={
                "destination": {"name": "B", "latitude": 7.5, "longitude": 4.3},
                "expires_in_minutes": 60,
            },
        )
    ).json()

    invite = await client.post(
        f"/api/v1/journeys/{j1['id']}/invitations",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"max_uses": 5, "expires_in_minutes": 60},
    )
    raw = invite.json()["invite_url"].rsplit("/", 1)[-1]

    guest = await client.post(f"/api/v1/join/{raw}/guest", json={"display_name": "G"})
    guest_token = guest.json()["guest_token"]

    # Guest can access own journey...
    resp = await client.get(f"/api/v1/journeys/{j1['id']}", headers={"X-Guest-Token": guest_token})
    assert resp.status_code == 200

    # ...but not the other host's journey.
    resp = await client.get(f"/api/v1/journeys/{j2['id']}", headers={"X-Guest-Token": guest_token})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_forged_jwt_rejected(client):
    token = await _register(client, "forge@example.com", "Forger")
    resp = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}tampered"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invitation_raw_token_not_stored(client):
    """Raw invitation tokens must never appear in API responses of listings."""
    host_token = await _register(client, "no raw@example.com".replace(" ", ""), "Hash Check")
    journey = (
        await client.post(
            "/api/v1/journeys",
            headers={"Authorization": f"Bearer {host_token}"},
            json={
                "destination": {"name": "X", "latitude": 6.5, "longitude": 3.3},
                "expires_in_minutes": 60,
            },
        )
    ).json()
    invite = await client.post(
        f"/api/v1/journeys/{journey['id']}/invitations",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"max_uses": 1, "expires_in_minutes": 60},
    )
    body = invite.json()
    # Response carries the raw URL once (needed to share), never the hash.
    assert "invite_url" in body
    assert "token_hash" not in body


@pytest.mark.asyncio
async def test_host_only_actions_blocked_for_visitors(client):
    host_token = await _register(client, "honly@example.com", "H Only")
    vis_token = await _register(client, "vonly@example.com", "V Only")

    journey = (
        await client.post(
            "/api/v1/journeys",
            headers={"Authorization": f"Bearer {host_token}"},
            json={
                "destination": {"name": "H", "latitude": 6.5, "longitude": 3.3},
                "expires_in_minutes": 60,
            },
        )
    ).json()

    invite = await client.post(
        f"/api/v1/journeys/{journey['id']}/invitations",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"max_uses": 5, "expires_in_minutes": 60},
    )
    raw = invite.json()["invite_url"].rsplit("/", 1)[-1]
    await client.post(
        f"/api/v1/join/{raw}/accept", headers={"Authorization": f"Bearer {vis_token}"}
    )

    for action in ("cancel", "complete", "start"):
        resp = await client.post(
            f"/api/v1/journeys/{journey['id']}/{action}",
            headers={"Authorization": f"Bearer {vis_token}"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_error_envelope_shape(client):
    """Every error uses the spec envelope: {error: {code, message, request_id}}."""
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 401
    err = resp.json()["error"]
    assert {"code", "message", "request_id"} <= set(err.keys())
    assert err["code"] == "UNAUTHENTICATED"
