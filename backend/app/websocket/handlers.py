"""WebSocket endpoint /ws/journeys/{journey_id} (spec §12).

Connection flow:
1. authenticate (access token or guest token)
2. resolve user/guest identity
3. verify journey membership
4. compute authorized location set (host sees all ACTIVE participants,
   visitors receive no other participants' locations in V1)
5. send authorized snapshot
6. receive pings; location updates arrive via manager broadcasts
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401
from sqlalchemy.orm import selectinload

from app.infrastructure.database import get_sessionmaker
from app.models.consent import LocationConsent
from app.models.guest_session import GuestSession
from app.models.journey import Journey
from app.models.participant import JourneyParticipant
from app.models.user import User
from app.security.jwt import decode_access_token
from app.security.tokens import hash_token
from app.websocket.manager import Connection, manager

router = APIRouter()


def _snapshot_for(journey: Journey, viewer_is_host: bool) -> dict:
    participants = []
    locations = []
    for p in journey.participants:
        participants.append(
            {
                "id": str(p.id),
                "role": p.role,
                "status": p.status,
                "display_name": (
                    p.guest_session.display_name
                    if p.guest_session is not None
                    else ("Host" if p.role == "HOST" else "Visitor")
                ),
                "joined_at": p.joined_at.isoformat() if p.joined_at else None,
                "left_at": p.left_at.isoformat() if p.left_at else None,
            }
        )
        if viewer_is_host and p.status == "ACTIVE":
            # Locations are pulled from Postgres latest; Redis holds live copies.
            locations.append(
                {
                    "participant_id": str(p.id),
                    "status": p.status,
                }
            )
    return {
        "type": "journey.snapshot",
        "journey": {
            "id": str(journey.id),
            "status": journey.status,
            "destination_name": journey.destination_name,
            "destination_lat": float(journey.destination_lat),
            "destination_lng": float(journey.destination_lng),
            "expires_at": journey.expires_at.isoformat(),
        },
        "participants": participants,
        "locations": locations,
    }


@router.websocket("/ws/journeys/{journey_id}")
async def journey_socket(websocket: WebSocket, journey_id: str, token: str = Query(default="")):
    session_factory = get_sessionmaker()
    async with session_factory() as db:  # type: AsyncSession
        # --- 1. authenticate ---
        user: User | None = None
        guest: GuestSession | None = None
        try:
            if token.startswith("guest:"):
                guest = (
                    await db.execute(
                        select(GuestSession).where(GuestSession.token_hash == hash_token(token[6:]))
                    )
                ).scalar_one_or_none()
                if guest is None or guest.is_expired or guest.status not in ("ACTIVE", "COMPLETED"):
                    await websocket.close(code=4401)
                    return
            else:
                payload = decode_access_token(token)
                user = await db.get(User, payload.get("sub"))
                if user is None or user.status != "ACTIVE":
                    await websocket.close(code=4401)
                    return
        except Exception:
            await websocket.close(code=4401)
            return

        # --- 2/3. journey membership ---
        journey = (
            await db.execute(
                select(Journey)
                .where(Journey.id == journey_id)
                .options(
                    selectinload(Journey.participants).selectinload(
                        JourneyParticipant.guest_session
                    )
                )
            )
        ).scalar_one_or_none()
        if journey is None:
            await websocket.close(code=4404)
            return

        membership = None
        for p in journey.participants:
            if user is not None and p.user_id == user.id:
                membership = p
                break
            if guest is not None and p.guest_session_id == guest.id:
                membership = p
                break
        if membership is None:
            await websocket.close(code=4403)
            return

        # --- 4. authorization scope ---
        viewer_is_host = user is not None and str(journey.host_user_id) == str(user.id)
        if viewer_is_host:
            authorized_ids = set()
            for p in journey.participants:
                if (
                    p.status == "ACTIVE"
                    and p.role == "VISITOR"
                    and await _has_active_consent(db, p.id)
                ):
                    authorized_ids.add(str(p.id))
        else:
            authorized_ids = set()  # visitors see no other participants' locations in V1

        conn = Connection(
            websocket=websocket,
            journey_id=str(journey.id),
            viewer_user_id=str(user.id) if user else None,
            viewer_guest_session_id=str(guest.id) if guest else None,
            authorized_participant_ids=authorized_ids,
            is_host=viewer_is_host,
        )
        await manager.connect(conn)

        # --- 5. snapshot ---
        try:
            await websocket.send_text(json.dumps(_snapshot_for(journey, viewer_is_host)))
            # --- 6. keep alive / client pings ---
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    if msg.get("type") == "ping":
                        await websocket.send_text(
                            json.dumps({"type": "pong", "ts": datetime.now(UTC).isoformat()})
                        )
                except (json.JSONDecodeError, ValueError):
                    continue
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(conn)


async def _has_active_consent(db: AsyncSession, participant_id) -> bool:
    """Authorization scope check at connect time.

    Consent is strictly re-verified at every location ingestion; this controls
    which location streams a host connection may receive.
    """
    consent = (
        await db.execute(
            select(LocationConsent).where(
                LocationConsent.participant_id == participant_id,
                LocationConsent.status == "GRANTED",
            )
        )
    ).scalar_one_or_none()
    return consent is not None and consent.is_active
