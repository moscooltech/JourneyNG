"""Journey lifecycle service (spec §9-11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.settings import get_settings
from app.core.errors import AppError, ErrorCode, ForbiddenError, NotFoundError
from app.core.timeutils import ensure_utc
from app.models.guest_session import GuestSession  # noqa: F401 — relationship target
from app.models.journey import Journey
from app.models.participant import TERMINAL_STATUSES, JourneyParticipant
from app.models.user import User
from app.schemas.journey import JourneyCreate
from app.services.state_machines import require_journey_transition


async def create_journey(db: AsyncSession, host: User, req: JourneyCreate) -> Journey:
    settings = get_settings()
    duration = timedelta(minutes=req.expires_in_minutes)
    if duration.total_seconds() < settings.journey_min_duration_minutes * 60:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Minimum journey duration is {settings.journey_min_duration_minutes} minutes.",
            422,
        )
    if duration.total_seconds() > settings.journey_max_duration_hours * 3600:
        raise AppError(
            ErrorCode.VALIDATION_ERROR,
            f"Maximum journey duration is {settings.journey_max_duration_hours} hours.",
            422,
        )

    journey = Journey(
        host_user_id=host.id,
        destination_name=req.destination.name,
        destination_lat=req.destination.latitude,
        destination_lng=req.destination.longitude,
        status="INVITED",
        expires_at=datetime.now(UTC) + duration,
    )
    db.add(journey)
    await db.flush()

    # Preferred implementation: host is a participant row so all participant
    # operations use one model (spec §7.6).
    db.add(
        JourneyParticipant(
            journey_id=journey.id,
            user_id=host.id,
            role="HOST",
            status="ACCEPTED",
            joined_at=datetime.now(UTC),
        )
    )
    await db.flush()
    return journey


async def get_journey_or_404(db: AsyncSession, journey_id: UUID) -> Journey:
    journey = (
        await db.execute(
            select(Journey)
            .where(Journey.id == journey_id)
            .options(
                selectinload(Journey.participants).selectinload(JourneyParticipant.guest_session)
            )
        )
    ).scalar_one_or_none()
    if journey is None:
        raise NotFoundError(ErrorCode.JOURNEY_NOT_FOUND, "Journey not found.")
    return journey


def get_participant_for_identity(
    journey: Journey, user_id: UUID | str | None, guest_session_id: UUID | str | None
) -> JourneyParticipant | None:
    """Identity args may be UUID or str; comparison is done on canonical strings."""
    uid = str(user_id) if user_id is not None else None
    gsid = str(guest_session_id) if guest_session_id is not None else None
    for p in journey.participants:
        if uid is not None and p.user_id is not None and str(p.user_id) == uid:
            return p
        if gsid is not None and p.guest_session_id is not None and str(p.guest_session_id) == gsid:
            return p
    return None


def require_membership(
    journey: Journey, user_id: UUID | str | None, guest_session_id: UUID | str | None
) -> JourneyParticipant:
    """Raises ForbiddenError when the requester is not a participant."""
    participant = get_participant_for_identity(journey, user_id, guest_session_id)
    if participant is None:
        raise ForbiddenError("You are not a participant of this journey.")
    return participant


def require_host(journey: Journey, user_id: UUID | str | None) -> None:
    if user_id is None or str(journey.host_user_id) != str(user_id):
        raise ForbiddenError("Host-only action.")


async def start_journey(db: AsyncSession, journey: Journey) -> Journey:
    _expire_if_needed(journey)
    if journey.status not in ("INVITED",):
        raise AppError(
            ErrorCode.JOURNEY_INVALID_TRANSITION,
            f"Cannot start journey from {journey.status} state.",
        )
    require_journey_transition(journey.status, "ACTIVE")
    journey.status = "ACTIVE"
    journey.started_at = datetime.now(UTC)
    await db.flush()
    return journey


async def cancel_journey(db: AsyncSession, journey: Journey) -> Journey:
    _expire_if_needed(journey)
    require_journey_transition(journey.status, "CANCELLED")
    journey.status = "CANCELLED"
    await db.flush()
    return journey


async def complete_journey(db: AsyncSession, journey: Journey) -> Journey:
    _expire_if_needed(journey)
    require_journey_transition(journey.status, "COMPLETED")
    journey.status = "COMPLETED"
    journey.completed_at = datetime.now(UTC)
    await db.flush()
    return journey


def _expire_if_needed(journey: Journey) -> None:
    if journey.status == "INVITED" and datetime.now(UTC) > ensure_utc(journey.expires_at):
        journey.status = "EXPIRED"


def maybe_complete_journey(journey: Journey) -> bool:
    """Marks journey COMPLETED when no participants remain active/pending (spec §10)."""
    if journey.status != "ACTIVE":
        return False
    active_states = {"ACCEPTED", "ACTIVE"}
    remaining = [
        p for p in journey.participants if p.role == "VISITOR" and p.status in active_states
    ]
    if remaining:
        return False
    visitors = [p for p in journey.participants if p.role == "VISITOR"]
    if visitors and all(p.status in TERMINAL_STATUSES | {"ARRIVED"} for p in visitors):
        journey.status = "COMPLETED"
        journey.completed_at = datetime.now(UTC)
        return True
    return False
