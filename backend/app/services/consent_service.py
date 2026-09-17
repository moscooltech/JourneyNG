"""Consent service — the heart of the privacy model.

Consent IS authorization: without an active GRANTED consent record for the
journey host as viewer, no location is accepted or shown.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode, ForbiddenError, NotFoundError
from app.models.consent import LocationConsent
from app.models.journey import Journey
from app.models.participant import JourneyParticipant
from app.services.state_machines import require_participant_transition

CONSENT_VERSION = "1"


async def grant_consent(
    db: AsyncSession,
    journey: Journey,
    participant: JourneyParticipant,
    scope: str = "LIVE_LOCATION",
    purpose: str = "TRAVEL_TO_DESTINATION",
    duration: str = "UNTIL_ARRIVAL",
) -> LocationConsent:
    """Grants consent for the current participant; viewer is the journey host."""
    if participant.role != "VISITOR":
        raise ForbiddenError("Only visitors grant location consent.")
    if journey.status not in ("INVITED", "ACTIVE"):
        raise AppError(ErrorCode.JOURNEY_NOT_ACTIVE, "Journey is not open for consent.", 409)

    # V1 viewer is always the host (spec §7.8).
    existing_active = (
        await db.execute(
            select(LocationConsent).where(
                LocationConsent.participant_id == participant.id,
                LocationConsent.status == "GRANTED",
            )
        )
    ).scalar_one_or_none()
    if existing_active is not None and existing_active.is_active:
        return existing_active

    now = datetime.now(UTC)
    expires_at = journey.expires_at if duration == "UNTIL_ARRIVAL" else journey.expires_at
    consent = LocationConsent(
        journey_id=journey.id,
        participant_id=participant.id,
        viewer_user_id=journey.host_user_id,
        purpose=purpose,
        scope=scope,
        status="GRANTED",
        granted_at=now,
        expires_at=expires_at,
        consent_version=CONSENT_VERSION,
    )
    db.add(consent)
    await db.flush()

    # Accepted -> ACTIVE when consent granted so participant can start sharing.
    if participant.status == "ACCEPTED":
        require_participant_transition(participant.status, "ACTIVE")
        participant.status = "ACTIVE"
        await db.flush()
    return consent


async def revoke_consent(
    db: AsyncSession, journey: Journey, participant: JourneyParticipant
) -> LocationConsent:
    now = datetime.now(UTC)
    consent = (
        await db.execute(
            select(LocationConsent).where(
                LocationConsent.participant_id == participant.id,
                LocationConsent.status == "GRANTED",
            )
        )
    ).scalar_one_or_none()
    if consent is None:
        raise NotFoundError(ErrorCode.CONSENT_NOT_FOUND, "No active consent found.")
    consent.status = "REVOKED"
    consent.revoked_at = now
    await db.flush()
    return consent


async def expire_consent(db: AsyncSession, participant_id: UUID) -> int:
    now = datetime.now(UTC)
    result = await db.execute(
        select(LocationConsent).where(
            LocationConsent.participant_id == participant_id,
            LocationConsent.status == "GRANTED",
            LocationConsent.expires_at <= now,
        )
    )
    consents = result.scalars().all()
    for c in consents:
        c.status = "EXPIRED"
    await db.flush()
    return len(consents)


async def require_active_consent(
    db: AsyncSession, participant: JourneyParticipant
) -> LocationConsent:
    """Hard gate: raises unless the participant has active GRANTED consent.

    Called on every location ingestion path (spec §11.6).
    """
    consent = (
        await db.execute(
            select(LocationConsent).where(
                LocationConsent.participant_id == participant.id,
                LocationConsent.status == "GRANTED",
            )
        )
    ).scalar_one_or_none()
    if consent is None:
        raise AppError(
            ErrorCode.CONSENT_REQUIRED,
            "Location sharing consent has not been granted.",
            403,
        )
    if not consent.is_active:
        consent.status = "EXPIRED"
        await db.flush()
        raise AppError(ErrorCode.CONSENT_REVOKED, "Location sharing consent has expired.", 403)
    return consent
