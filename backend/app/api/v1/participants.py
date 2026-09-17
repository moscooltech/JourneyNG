"""Participant + consent endpoints (spec §11.4, §11.5)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthenticatedError
from app.infrastructure.database import get_db
from app.models.consent import LocationConsent
from app.schemas.journey import ConsentGrant
from app.security.authorization import Requester, get_requester
from app.services import consent_service, journey_service, participant_service

router = APIRouter(prefix="/journeys/{journey_id}", tags=["participants", "consent"])


def _resolve_participant(journey, requester: Requester):
    return journey_service.require_membership(
        journey, requester.user_id, requester.guest_session_id
    )


@router.post("/consent", status_code=200)
async def grant_consent(
    journey_id: UUID,
    req: ConsentGrant,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    consent = await consent_service.grant_consent(
        db, journey, participant, req.scope, req.purpose, req.duration
    )
    return {
        "status": consent.status,
        "granted_at": consent.granted_at.isoformat(),
        "expires_at": consent.expires_at.isoformat(),
        "viewer": {"user_id": str(consent.viewer_user_id)},
    }


@router.post("/consent/revoke", status_code=200)
async def revoke_consent(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    consent = await consent_service.revoke_consent(db, journey, participant)
    return {
        "status": consent.status,
        "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
    }


@router.get("/consent", status_code=200)
async def get_consent(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    consents = (
        await db.execute(
            select(LocationConsent).where(LocationConsent.participant_id == participant.id)
        )
    ).scalars()
    return [
        {
            "id": str(c.id),
            "status": c.status,
            "purpose": c.purpose,
            "scope": c.scope,
            "granted_at": c.granted_at.isoformat(),
            "expires_at": c.expires_at.isoformat(),
            "viewer_user_id": str(c.viewer_user_id),
        }
        for c in consents
    ]


@router.post("/participants/me/start", status_code=200)
async def start_my_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    participant = await participant_service.start_participant_journey(db, journey, participant)
    return {"participant_id": str(participant.id), "status": participant.status}


@router.post("/participants/me/leave", status_code=200)
async def leave_journey(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    participant = await participant_service.leave_journey(db, journey, participant)
    return {"participant_id": str(participant.id), "status": participant.status}


@router.post("/participants/me/arrive", status_code=200)
async def arrive(
    journey_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = _resolve_participant(journey, requester)
    participant = await participant_service.mark_arrived(db, journey, participant)
    return {"participant_id": str(participant.id), "status": participant.status}


@router.post("/participants/{participant_id}/remove", status_code=200)
async def remove_participant(
    journey_id: UUID,
    participant_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    journey = await journey_service.get_journey_or_404(db, journey_id)
    participant = await participant_service.remove_participant(db, journey, participant_id, user.id)
    return {"participant_id": str(participant.id), "status": participant.status}
