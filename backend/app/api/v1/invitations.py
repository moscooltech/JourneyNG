"""Invitation endpoints (spec §11.3)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError, UnauthenticatedError
from app.infrastructure.database import get_db
from app.models.invitation import JourneyInvitation
from app.schemas.journey import GuestJoin, InvitationCreate
from app.security.authorization import Requester, get_requester
from app.security.rate_limit import enforce_rate_limit
from app.services import invitation_service, journey_service

router = APIRouter(tags=["invitations"])


@router.post("/journeys/{journey_id}/invitations", status_code=201)
async def create_invitation(
    journey_id: UUID,
    req: InvitationCreate,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_host(journey, user.id)

    invitation, raw_token = await invitation_service.create_invitation(
        db, journey, user.id, req.max_uses, req.expires_in_minutes
    )
    return {
        "invitation_id": str(invitation.id),
        "invite_url": f"https://app.example.com/join/{raw_token}",
        "expires_at": invitation.expires_at.isoformat(),
        "max_uses": invitation.max_uses,
    }


@router.post("/journeys/{journey_id}/invitations/{invitation_id}/revoke", status_code=200)
async def revoke_invitation(
    journey_id: UUID,
    invitation_id: UUID,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    journey = await journey_service.get_journey_or_404(db, journey_id)
    journey_service.require_host(journey, user.id)

    invitation = (
        await db.execute(
            select(JourneyInvitation).where(
                JourneyInvitation.id == invitation_id,
                JourneyInvitation.journey_id == journey_id,
            )
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise NotFoundError(ErrorCode.INVITATION_NOT_FOUND, "Invitation not found.")
    invitation.revoked_at = datetime.now(UTC)
    await db.flush()
    return {"status": "revoked"}


@router.post("/join/{token}/guest", status_code=201)
async def join_as_guest(
    token: str,
    req: GuestJoin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    await enforce_rate_limit("join", request.client.host if request.client else "unknown", 10)
    journey, participant, guest_token = await invitation_service.join_as_guest(
        db, token, req.display_name
    )
    return {
        "journey_id": str(journey.id),
        "participant_id": str(participant.id),
        "guest_token": guest_token,
        "status": participant.status,
    }


@router.post("/join/{token}/accept", status_code=200)
async def accept_invitation(
    token: str,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Registered user accepts an invitation."""
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    display_name = user.profile.display_name if user.profile else "Visitor"
    journey, participant = await invitation_service.join_as_registered(
        db, token, user.id, display_name
    )
    return {
        "journey_id": str(journey.id),
        "participant_id": str(participant.id),
        "status": participant.status,
    }


@router.post("/join/{token}/decline", status_code=200)
async def decline_invitation(
    token: str,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    from app.services.state_machines import require_participant_transition

    journey, _invitation = await invitation_service.redeem_token(db, token)
    participant = journey_service.get_participant_for_identity(
        journey, user.id, requester.guest_session_id
    )
    if participant is None:
        participant = journey_service.get_participant_for_identity(journey, user.id, None)
    if participant is None:
        raise NotFoundError(ErrorCode.PARTICIPANT_NOT_FOUND, "You are not invited to this journey.")
    require_participant_transition(participant.status, "DECLINED")
    participant.status = "DECLINED"
    await db.flush()
    return {"journey_id": str(journey.id), "status": participant.status}
