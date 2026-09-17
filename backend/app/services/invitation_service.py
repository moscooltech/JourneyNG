"""Invitation service: secure token creation, redemption, guest sessions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.errors import (
    AppError,
    ConflictError,
    ErrorCode,
    NotFoundError,
)
from app.core.timeutils import ensure_utc
from app.models.guest_session import GuestSession
from app.models.invitation import JourneyInvitation
from app.models.journey import Journey
from app.models.participant import JourneyParticipant
from app.security.tokens import generate_token, hash_token


async def create_invitation(
    db: AsyncSession, journey: Journey, created_by, max_uses: int | None, expires_in_minutes: int
) -> tuple[JourneyInvitation, str]:
    """Returns (invitation, raw_token). Raw token is never stored server-side."""
    settings = get_settings()
    raw = generate_token(24)
    invitation = JourneyInvitation(
        journey_id=journey.id,
        token_hash=hash_token(raw),
        created_by=created_by,
        max_uses=max_uses if max_uses is not None else settings.invitation_max_uses_default,
        expires_at=datetime.now(UTC) + timedelta(minutes=expires_in_minutes),
    )
    db.add(invitation)
    await db.flush()
    return invitation, raw


async def redeem_token(db: AsyncSession, raw_token: str) -> tuple[Journey, JourneyInvitation]:
    """Validates an invitation token and returns the journey + invitation."""
    invitation = (
        await db.execute(
            select(JourneyInvitation).where(JourneyInvitation.token_hash == hash_token(raw_token))
        )
    ).scalar_one_or_none()
    if invitation is None:
        raise NotFoundError(ErrorCode.INVALID_INVITATION_TOKEN, "Invitation not found.")
    if invitation.revoked_at is not None:
        raise AppError(ErrorCode.INVITATION_REVOKED, "This invitation was revoked.", 410)
    if ensure_utc(invitation.expires_at) < datetime.now(UTC):
        raise AppError(ErrorCode.INVITATION_EXPIRED, "This invitation expired.", 410)
    if invitation.is_exhausted:
        raise AppError(ErrorCode.INVITATION_EXHAUSTED, "This invitation has no uses left.", 410)

    journey = await db.get(Journey, invitation.journey_id)
    if journey is None:
        raise NotFoundError(ErrorCode.JOURNEY_NOT_FOUND, "Journey not found.")
    return journey, invitation


async def join_as_guest(
    db: AsyncSession, raw_token: str, display_name: str
) -> tuple[Journey, JourneyParticipant, str]:
    """Creates guest session + participant; returns (journey, participant, guest_token)."""
    journey, invitation = await redeem_token(db, raw_token)
    settings = get_settings()

    if journey.status not in ("INVITED", "ACTIVE"):
        raise AppError(ErrorCode.JOURNEY_NOT_ACTIVE, "This journey is no longer open.", 410)

    active_count = (
        await db.execute(
            select(JourneyParticipant).where(
                JourneyParticipant.journey_id == journey.id,
                JourneyParticipant.role == "VISITOR",
                JourneyParticipant.status.in_(["INVITED", "ACCEPTED", "ACTIVE", "ARRIVED"]),
            )
        )
    ).scalars()
    visitors = list(active_count)
    if len(visitors) >= settings.max_active_participants:
        raise AppError(
            ErrorCode.PARTICIPANT_LIMIT_REACHED,
            "This journey has reached its participant limit.",
            409,
        )

    raw_guest = generate_token(32)
    guest = GuestSession(
        journey_id=journey.id,
        display_name=display_name,
        token_hash=hash_token(raw_guest),
        status="ACTIVE",
        expires_at=journey.expires_at,
    )
    db.add(guest)
    await db.flush()

    participant = JourneyParticipant(
        journey_id=journey.id,
        guest_session_id=guest.id,
        role="VISITOR",
        status="ACCEPTED",
        joined_at=datetime.now(UTC),
    )
    db.add(participant)

    invitation.use_count += 1
    if invitation.max_uses is not None and invitation.use_count >= invitation.max_uses:
        invitation.used_at = datetime.now(UTC)
    await db.flush()
    return journey, participant, raw_guest


async def join_as_registered(
    db: AsyncSession, raw_token: str, user_id, display_name: str
) -> tuple[Journey, JourneyParticipant]:
    """Accepts an invitation as a registered user."""
    journey, invitation = await redeem_token(db, raw_token)
    if journey.status not in ("INVITED", "ACTIVE"):
        raise AppError(ErrorCode.JOURNEY_NOT_ACTIVE, "This journey is no longer open.", 410)

    existing = (
        await db.execute(
            select(JourneyParticipant).where(
                JourneyParticipant.journey_id == journey.id,
                JourneyParticipant.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.status in ("DECLINED", "LEFT", "REMOVED"):
            raise ConflictError(ErrorCode.CONFLICT, "You have already left or were removed.")
        return journey, existing

    participant = JourneyParticipant(
        journey_id=journey.id,
        user_id=user_id,
        role="VISITOR",
        status="ACCEPTED",
        joined_at=datetime.now(UTC),
    )
    db.add(participant)
    invitation.use_count += 1
    await db.flush()
    return journey, participant
