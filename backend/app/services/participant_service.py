"""Participant service: start, leave, arrive, remove (spec §11.5)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode, ForbiddenError, NotFoundError
from app.core.logging import get_logger
from app.models.journey import Journey
from app.models.participant import JourneyParticipant
from app.services import journey_service
from app.services.consent_service import require_active_consent
from app.services.state_machines import require_participant_transition

logger = get_logger(__name__)


async def start_participant_journey(
    db: AsyncSession, journey: Journey, participant: JourneyParticipant
) -> JourneyParticipant:
    """Starts a visitor's sharing: requires accepted state + active consent."""
    if journey.status == "INVITED":
        # Host must have started the journey first for visitors to share.
        pass  # Allowed: consent can be granted pre-start; actual sharing gates on ACTIVE.
    if participant.role == "HOST":
        raise ForbiddenError("Hosts do not start their own sharing session.")

    await require_active_consent(db, participant)

    if participant.status not in ("ACCEPTED", "ACTIVE"):
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            f"Cannot start sharing from {participant.status} state.",
        )

    if participant.status == "ACCEPTED":
        require_participant_transition(participant.status, "ACTIVE")
        participant.status = "ACTIVE"
    await db.flush()
    return participant


async def leave_journey(
    db: AsyncSession, journey: Journey, participant: JourneyParticipant
) -> JourneyParticipant:
    if participant.role == "HOST":
        raise ForbiddenError("Hosts end the journey instead of leaving it.")

    if participant.status == "ACTIVE":
        require_participant_transition("ACTIVE", "LEFT")
    elif participant.status == "ACCEPTED":
        require_participant_transition("ACCEPTED", "LEFT")
    else:
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            f"Cannot leave from {participant.status} state.",
        )

    participant.status = "LEFT"
    participant.left_at = datetime.now(UTC)
    await db.flush()
    journey_service.maybe_complete_journey(journey)
    return participant


async def mark_arrived(
    db: AsyncSession, journey: Journey, participant: JourneyParticipant
) -> JourneyParticipant:
    if participant.status != "ACTIVE":
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            "Only actively sharing participants can confirm arrival.",
        )
    require_participant_transition("ACTIVE", "ARRIVED")
    participant.status = "ARRIVED"
    await db.flush()

    # Arrival ends consent and location sharing for this participant only.
    from app.services.consent_service import revoke_consent

    try:
        await revoke_consent(db, journey, participant)
    except NotFoundError:
        logger.info("arrival_no_consent_to_revoke")
    journey_service.maybe_complete_journey(journey)
    return participant


async def remove_participant(
    db: AsyncSession, journey: Journey, participant_id: UUID, acting_host_id
) -> JourneyParticipant:
    journey_service.require_host(journey, acting_host_id)
    participant = (
        await db.execute(
            select(JourneyParticipant).where(
                JourneyParticipant.id == participant_id,
                JourneyParticipant.journey_id == journey.id,
            )
        )
    ).scalar_one_or_none()
    if participant is None:
        raise NotFoundError(ErrorCode.PARTICIPANT_NOT_FOUND, "Participant not found.")
    if participant.role == "HOST":
        raise ForbiddenError("The host cannot be removed.")
    if participant.status not in ("INVITED", "ACCEPTED", "ACTIVE"):
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            f"Cannot remove a participant in {participant.status} state.",
        )
    participant.status = "REMOVED"
    participant.left_at = datetime.now(UTC)
    await db.flush()

    await revoke_consent_if_any(db, participant)
    journey_service.maybe_complete_journey(journey)
    return participant


async def revoke_consent_if_any(db: AsyncSession, participant: JourneyParticipant) -> None:
    from app.services.consent_service import revoke_consent

    try:
        await revoke_consent(db, participant.journey, participant)
    except Exception:
        logger.info("remove_no_consent_to_revoke")
