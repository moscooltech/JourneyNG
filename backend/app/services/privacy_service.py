"""Privacy service (spec §24, §11.7): active sharing visibility, stop-all."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consent import LocationConsent
from app.models.journey import Journey
from app.models.participant import JourneyParticipant


async def active_sharing_for_user(db: AsyncSession, user_id) -> list[dict]:
    """Returns the user's active sharing relationships (who can see them, why, until when)."""
    stmt = (
        select(LocationConsent, Journey, JourneyParticipant)
        .join(Journey, LocationConsent.journey_id == Journey.id)
        .join(JourneyParticipant, LocationConsent.participant_id == JourneyParticipant.id)
        .where(
            JourneyParticipant.user_id == user_id,
            LocationConsent.status == "GRANTED",
        )
    )
    rows = (await db.execute(stmt)).all()
    results = []
    for consent, journey, participant in rows:
        if not consent.is_active:
            continue
        results.append(
            {
                "journey_id": str(journey.id),
                "destination": journey.destination_name,
                "purpose": consent.purpose,
                "scope": consent.scope,
                "granted_at": consent.granted_at.isoformat(),
                "expires_at": consent.expires_at.isoformat(),
                "status": consent.status,
                "participant_id": str(participant.id),
            }
        )
    return results


async def stop_all_sharing(db: AsyncSession, user_id) -> int:
    """Revokes all active consents for the user's participants. Returns count."""
    stmt = (
        select(LocationConsent, JourneyParticipant)
        .join(JourneyParticipant, LocationConsent.participant_id == JourneyParticipant.id)
        .where(
            JourneyParticipant.user_id == user_id,
            LocationConsent.status == "GRANTED",
        )
    )
    rows = (await db.execute(stmt)).all()
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    count = 0
    for consent, _participant in rows:
        consent.status = "REVOKED"
        consent.revoked_at = now
        count += 1
    await db.flush()
    return count
