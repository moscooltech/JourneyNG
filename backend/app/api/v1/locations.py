"""Location endpoints (spec §11.6)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import get_settings
from app.core.errors import ForbiddenError
from app.infrastructure.database import get_db
from app.models.location_latest import LocationLatest
from app.models.participant import JourneyParticipant
from app.schemas.journey import LocationAccepted, LocationUpdate
from app.security.authorization import Requester, get_requester
from app.security.rate_limit import enforce_rate_limit
from app.services import journey_service, location_service

router = APIRouter(prefix="/journeys/{journey_id}", tags=["locations"])


@router.post("/location", response_model=LocationAccepted)
async def upload_location(
    journey_id: UUID,
    req: LocationUpdate,
    request: Request,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> LocationAccepted:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = journey_service.require_membership(
        journey, requester.user_id, requester.guest_session_id
    )

    await enforce_rate_limit(
        "location", str(participant.id), get_settings().rate_limit_location_per_min
    )

    sequence = await location_service.ingest_location(
        db,
        journey,
        participant,
        req.latitude,
        req.longitude,
        req.accuracy_m,
        req.speed_mps,
        req.heading,
        req.altitude_m,
        req.recorded_at,
    )
    return LocationAccepted(
        accepted=True,
        server_received_at=datetime.now(UTC),
        server_sequence=sequence,
    )


@router.get("/locations")
async def get_locations(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Host-only (V1) — current authorized ACTIVE participant locations."""
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_membership(journey, requester.user_id, requester.guest_session_id)

    is_host = requester.user_id is not None and str(journey.host_user_id) == str(requester.user_id)
    if not is_host:
        raise ForbiddenError("Only the host can view participant locations.")

    rows = (
        await db.execute(
            select(LocationLatest, JourneyParticipant)
            .join(
                JourneyParticipant,
                LocationLatest.participant_id == JourneyParticipant.id,
            )
            .options(selectinload(JourneyParticipant.guest_session))
            .where(
                LocationLatest.journey_id == journey.id,
                JourneyParticipant.status == "ACTIVE",
            )
        )
    ).all()

    settings = get_settings()
    now = datetime.now(UTC)
    results = []
    for loc, participant in rows:
        received = (
            loc.received_at if loc.received_at.tzinfo else loc.received_at.replace(tzinfo=UTC)
        )
        age = (now - received).total_seconds()
        freshness = (
            "LIVE"
            if age < settings.location_stale_after_seconds
            else "STALE"
            if age < settings.location_offline_after_seconds
            else "OFFLINE"
        )
        results.append(
            {
                "participant_id": str(participant.id),
                "display_name": (
                    participant.guest_session.display_name
                    if participant.guest_session is not None
                    else "Visitor"
                ),
                "latitude": float(loc.latitude),
                "longitude": float(loc.longitude),
                "accuracy_m": loc.accuracy_m,
                "speed_mps": loc.speed_mps,
                "heading": loc.heading,
                "recorded_at": loc.recorded_at.isoformat(),
                "received_at": loc.received_at.isoformat(),
                "freshness": freshness,
            }
        )
    return results
