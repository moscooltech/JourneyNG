"""Journey endpoints (spec §11.2)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError
from app.infrastructure.database import get_db
from app.models.journey import Journey
from app.models.participant import JourneyParticipant
from app.schemas.journey import JourneyCreate, JourneyDetail, JourneyOut, ParticipantOut
from app.security.authorization import Requester, get_requester
from app.services import journey_service

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.post("", response_model=JourneyOut, status_code=201)
async def create_journey(
    req: JourneyCreate,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> JourneyOut:
    user = await _require_registered(requester)
    journey = await journey_service.create_journey(db, user, req)
    return JourneyOut.model_validate(journey)


async def _require_registered(requester: Requester):
    if requester.user is None:
        raise ForbiddenError("Registered account required.")
    return requester.user


@router.get("", response_model=list[JourneyOut])
async def list_journeys(
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> list[JourneyOut]:
    user = await _require_registered(requester)
    stmt = (
        select(Journey)
        .join(JourneyParticipant, JourneyParticipant.journey_id == Journey.id)
        .where(JourneyParticipant.user_id == user.id)
        .order_by(Journey.created_at.desc())
        .limit(100)
    )
    journeys = (await db.execute(stmt)).scalars().unique().all()
    return [JourneyOut.model_validate(j) for j in journeys]


@router.get("/{journey_id}", response_model=JourneyDetail)
async def get_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> JourneyDetail:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = journey_service.require_membership(
        journey, requester.user_id, requester.guest_session_id
    )
    is_host = journey.host_user_id == requester.user_id
    return JourneyDetail(
        journey=JourneyOut.model_validate(journey),
        participants=[
            ParticipantOut(
                id=p.id,
                role=p.role,
                status=p.status,
                display_name=_participant_display_name(p),
                user_id=p.user_id,
                joined_at=p.joined_at,
                left_at=p.left_at,
            )
            for p in journey.participants
        ],
        viewer_role=participant.role,
        is_host=is_host,
    )


def _participant_display_name(p: JourneyParticipant) -> str:
    if p.role == "HOST":
        return "Host"
    if p.guest_session is not None:
        return p.guest_session.display_name
    return "Visitor"


@router.post("/{journey_id}/start", response_model=JourneyOut)
async def start_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> JourneyOut:
    user = await _require_registered(requester)
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_host(journey, user.id)
    journey = await journey_service.start_journey(db, journey)
    return JourneyOut.model_validate(journey)


@router.post("/{journey_id}/cancel", response_model=JourneyOut)
async def cancel_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> JourneyOut:
    user = await _require_registered(requester)
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_host(journey, user.id)
    journey = await journey_service.cancel_journey(db, journey)
    return JourneyOut.model_validate(journey)


@router.post("/{journey_id}/complete", response_model=JourneyOut)
async def complete_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> JourneyOut:
    user = await _require_registered(requester)
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_host(journey, user.id)
    journey = await journey_service.complete_journey(db, journey)
    return JourneyOut.model_validate(journey)
