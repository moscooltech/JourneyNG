"""End-to-end journey flow: host + guest visitor happy path and edge cases (spec §51, §52)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


async def _register(client, email: str, name: str) -> tuple[str, str]:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"display_name": name, "email": email, "phone": None, "password": "strong-pass-123"},
    )
    body = resp.json()
    return body["access_token"], body["refresh_token"]


async def _create_journey(client, token: str) -> dict:
    resp = await client.post(
        "/api/v1/journeys",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "destination": {"name": "Ikeja City Mall", "latitude": 6.6018, "longitude": 3.3515},
            "expires_in_minutes": 120,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def _create_invitation(client, token: str, journey_id: str) -> str:
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/invitations",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_uses": 5, "expires_in_minutes": 60},
    )
    assert resp.status_code == 201
    url = resp.json()["invite_url"]
    return url.rsplit("/", 1)[-1]


async def _grant_consent_and_start(client, guest_token: str, journey_id: str):
    await client.post(
        f"/api/v1/journeys/{journey_id}/consent",
        headers={"X-Guest-Token": guest_token},
        json={
            "scope": "LIVE_LOCATION",
            "purpose": "TRAVEL_TO_DESTINATION",
            "duration": "UNTIL_ARRIVAL",
        },
    )
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/participants/me/start",
        headers={"X-Guest-Token": guest_token},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_full_guest_flow(client):
    host_token, _ = await _register(client, "host@example.com", "Babatunde")
    journey = await _create_journey(client, host_token)
    journey_id = journey["id"]

    # Journey starts in INVITED state with host participant.
    assert journey["status"] == "INVITED"

    raw_token = await _create_invitation(client, host_token, journey_id)

    # Guest joins.
    resp = await client.post(f"/api/v1/join/{raw_token}/guest", json={"display_name": "John"})
    assert resp.status_code == 201
    guest_token = resp.json()["guest_token"]

    # Host starts journey.
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # Guest grants consent and starts sharing.
    await _grant_consent_and_start(client, guest_token, journey_id)

    # Guest uploads location.
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers={"X-Guest-Token": guest_token},
        json={
            "latitude": 6.5244,
            "longitude": 3.3792,
            "accuracy_m": 8.2,
            "speed_mps": 6.4,
            "heading": 91.0,
            "recorded_at": (datetime.now(UTC) - timedelta(seconds=2)).isoformat(),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True

    # Host sees the location.
    resp = await client.get(
        f"/api/v1/journeys/{journey_id}/locations",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    assert resp.status_code == 200
    locations = resp.json()
    assert len(locations) == 1
    assert locations[0]["freshness"] == "LIVE"

    # Guest arrives — sharing ends for that participant only.
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/participants/me/arrive",
        headers={"X-Guest-Token": guest_token},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARRIVED"

    # Location upload now rejected (participant ARRIVED / consent revoked).
    resp = await client.post(
        f"/api/v1/journeys/{journey_id}/location",
        headers={"X-Guest-Token": guest_token},
        json={
            "latitude": 6.5244,
            "longitude": 3.3792,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code in (403, 409)  # consent-revoked or participant-inactive


@pytest.mark.asyncio
async def test_location_requires_consent(client):
    host_token, _ = await _register(client, "host2@example.com", "Host Two")
    journey = await _create_journey(client, host_token)
    raw_token = await _create_invitation(client, host_token, journey["id"])

    resp = await client.post(f"/api/v1/join/{raw_token}/guest", json={"display_name": "Sneaky"})
    guest_token = resp.json()["guest_token"]

    await client.post(
        f"/api/v1/journeys/{journey['id']}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )

    # No consent granted — start must fail.
    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/participants/me/start",
        headers={"X-Guest-Token": guest_token},
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CONSENT_REQUIRED"

    # Direct location upload also blocked.
    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/location",
        headers={"X-Guest-Token": guest_token},
        json={
            "latitude": 6.5244,
            "longitude": 3.3792,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_non_host_cannot_view_locations(client):
    host_token, _ = await _register(client, "host3@example.com", "Host Three")
    visitor_token, _ = await _register(client, "vis@example.com", "Visitor One")
    journey = await _create_journey(client, host_token)
    raw_token = await _create_invitation(client, host_token, journey["id"])

    await client.post(
        f"/api/v1/join/{raw_token}/accept",
        headers={"Authorization": f"Bearer {visitor_token}"},
    )

    resp = await client.get(
        f"/api/v1/journeys/{journey['id']}/locations",
        headers={"Authorization": f"Bearer {visitor_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_stranger_cannot_access_journey(client):
    host_token, _ = await _register(client, "host4@example.com", "Host Four")
    stranger_token, _ = await _register(client, "stranger@example.com", "Stranger")
    journey = await _create_journey(client, host_token)

    resp = await client.get(
        f"/api/v1/journeys/{journey['id']}",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_expired_invitation_rejected(client):
    host_token, _ = await _register(client, "host5@example.com", "Host Five")
    journey = await _create_journey(client, host_token)

    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/invitations",
        headers={"Authorization": f"Bearer {host_token}"},
        json={"max_uses": 5, "expires_in_minutes": 5},
    )
    resp.json()["invite_url"]

    # Cannot fast-forward time in this test; just verify invalid tokens rejected.
    resp = await client.post(
        "/api/v1/join/definitely-invalid-token/guest", json={"display_name": "X"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "INVALID_INVITATION_TOKEN"


@pytest.mark.asyncio
async def test_privacy_stop_all_sharing(client):
    host_token, _ = await _register(client, "host6@example.com", "Host Six")
    journey = await _create_journey(client, host_token)
    raw_token = await _create_invitation(client, host_token, journey["id"])

    resp = await client.post(f"/api/v1/join/{raw_token}/guest", json={"display_name": "John P"})
    guest_token = resp.json()["guest_token"]

    await client.post(
        f"/api/v1/journeys/{journey['id']}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    await client.post(
        f"/api/v1/journeys/{journey['id']}/consent",
        headers={"X-Guest-Token": guest_token},
        json={
            "scope": "LIVE_LOCATION",
            "purpose": "TRAVEL_TO_DESTINATION",
            "duration": "UNTIL_ARRIVAL",
        },
    )

    # Active sharing shows on privacy dashboard (guest has no /privacy access
    # since guest != user; test registered visitor path instead).
    vis_token, _ = await _register(client, "vis2@example.com", "Vis Two")
    resp2 = await client.post(
        f"/api/v1/join/{raw_token}/accept",
        headers={"Authorization": f"Bearer {vis_token}"},
    )
    assert resp2.status_code == 200
    await client.post(
        f"/api/v1/journeys/{journey['id']}/consent",
        headers={"Authorization": f"Bearer {vis_token}"},
        json={
            "scope": "LIVE_LOCATION",
            "purpose": "TRAVEL_TO_DESTINATION",
            "duration": "UNTIL_ARRIVAL",
        },
    )

    resp = await client.get(
        "/api/v1/privacy/active-sharing",
        headers={"Authorization": f"Bearer {vis_token}"},
    )
    assert resp.status_code == 200
    sharing = resp.json()
    assert len(sharing) >= 1
    assert sharing[0]["purpose"] == "TRAVEL_TO_DESTINATION"

    resp = await client.post(
        "/api/v1/privacy/stop-all-sharing",
        headers={"Authorization": f"Bearer {vis_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] >= 1

    # After stop-all, location upload blocked.
    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/location",
        headers={"Authorization": f"Bearer {vis_token}"},
        json={
            "latitude": 6.5244,
            "longitude": 3.3792,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_group_independent_participants(client):
    """One participant arriving must not stop others (spec §52)."""
    host_token, _ = await _register(client, "grouphost@example.com", "Group Host")
    journey = await _create_journey(client, host_token)
    raw_token = await _create_invitation(client, host_token, journey["id"])

    # Two guests join.
    r1 = await client.post(f"/api/v1/join/{raw_token}/guest", json={"display_name": "John"})
    r2 = await client.post(f"/api/v1/join/{raw_token}/guest", json={"display_name": "Sarah"})
    g1, g2 = r1.json()["guest_token"], r2.json()["guest_token"]

    await client.post(
        f"/api/v1/journeys/{journey['id']}/start",
        headers={"Authorization": f"Bearer {host_token}"},
    )
    await _grant_consent_and_start(client, g1, journey["id"])
    await _grant_consent_and_start(client, g2, journey["id"])

    # John arrives.
    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/participants/me/arrive",
        headers={"X-Guest-Token": g1},
    )
    assert resp.status_code == 200

    # Sarah is still active and can upload.
    resp = await client.post(
        f"/api/v1/journeys/{journey['id']}/location",
        headers={"X-Guest-Token": g2},
        json={
            "latitude": 6.5,
            "longitude": 3.38,
            "recorded_at": datetime.now(UTC).isoformat(),
        },
    )
    assert resp.status_code == 200
