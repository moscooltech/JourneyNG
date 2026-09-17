"""Location ingestion service.

Server-side validation pipeline (spec §11.6, §32):
1. participant belongs to journey (identity from auth, never client-supplied)
2. participant ACTIVE
3. consent GRANTED and unexpired (hard gate)
4. journey ACTIVE
5. coordinate/timestamp sanity
6. Redis live state (TTL) + Postgres location_latest; WebSocket broadcast
"""

from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.errors import AppError, ErrorCode
from app.core.logging import get_logger
from app.infrastructure.redis import get_redis
from app.models.journey import Journey
from app.models.location_latest import LocationLatest
from app.models.participant import JourneyParticipant
from app.services.consent_service import require_active_consent

logger = get_logger(__name__)


def validate_coordinates(latitude: float, longitude: float, accuracy_m: float | None) -> None:
    if math.isnan(latitude) or math.isnan(longitude):
        raise AppError(ErrorCode.LOCATION_REJECTED, "Invalid coordinates.", 422)
    if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
        raise AppError(ErrorCode.LOCATION_REJECTED, "Coordinates out of range.", 422)
    settings = get_settings()
    if accuracy_m is not None and accuracy_m > settings.location_max_accuracy_m:
        raise AppError(ErrorCode.LOCATION_REJECTED, "Location accuracy too poor to share.", 422)


def validate_timestamp(recorded_at: datetime) -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    recorded = recorded_at if recorded_at.tzinfo else recorded_at.replace(tzinfo=UTC)
    if recorded > now + timedelta(seconds=settings.location_max_clock_skew_seconds):
        raise AppError(ErrorCode.LOCATION_REJECTED, "Timestamp is in the future.", 422)
    if (now - recorded).total_seconds() > settings.location_max_age_seconds:
        raise AppError(ErrorCode.LOCATION_REJECTED, "Location update is too old.", 422)


async def ingest_location(
    db: AsyncSession,
    journey: Journey,
    participant: JourneyParticipant,
    latitude: float,
    longitude: float,
    accuracy_m: float | None,
    speed_mps: float | None,
    heading: float | None,
    altitude_m: float | None,
    recorded_at: datetime,
) -> int:
    """Full authorization + validation pipeline. Returns server_sequence."""
    settings = get_settings()

    # 1. journey must be ACTIVE
    if journey.status != "ACTIVE":
        raise AppError(ErrorCode.JOURNEY_NOT_ACTIVE, "Journey is not active.", 409)

    # 2. participant must be ACTIVE
    if participant.status != "ACTIVE":
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            "Participant is not actively sharing.",
            403,
        )

    # 3. consent hard gate
    await require_active_consent(db, participant)

    # 4. payload validation
    validate_coordinates(latitude, longitude, accuracy_m)
    validate_timestamp(recorded_at)

    # 5. sequence
    seq_key = f"journey:{journey.id}:participant:{participant.id}:seq"
    sequence = 1
    try:
        client = get_redis()
        sequence = int(await client.incr(seq_key))
        await client.expire(seq_key, 86400)
    except Exception:
        last = (
            await db.execute(
                select(LocationLatest.server_sequence)
                .where(LocationLatest.journey_id == journey.id)
                .order_by(LocationLatest.server_sequence.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        sequence = (last or 0) + 1

    received_at = datetime.now(UTC)

    # 6. persist latest location (temporary; cleanup worker handles deletion)
    row = await db.get(LocationLatest, participant.id)
    if row is None:
        row = LocationLatest(participant_id=participant.id)
        db.add(row)
    row.journey_id = journey.id
    row.latitude = Decimal(str(latitude))
    row.longitude = Decimal(str(longitude))
    row.accuracy_m = accuracy_m
    row.speed_mps = speed_mps
    row.heading = heading
    row.altitude_m = altitude_m
    row.recorded_at = recorded_at if recorded_at.tzinfo else recorded_at.replace(tzinfo=UTC)
    row.received_at = received_at
    row.server_sequence = sequence
    await db.flush()

    # 7. Redis live state with TTL (degrades safely when unavailable)
    try:
        client = get_redis()
        payload = json.dumps(
            {
                "participant_id": str(participant.id),
                "latitude": latitude,
                "longitude": longitude,
                "accuracy_m": accuracy_m,
                "speed_mps": speed_mps,
                "heading": heading,
                "recorded_at": row.recorded_at.isoformat(),
                "received_at": received_at.isoformat(),
                "server_sequence": sequence,
            }
        )
        ttl = settings.location_retention_hours * 3600
        await client.set(
            f"journey:{journey.id}:participant:{participant.id}:location",
            payload,
            ex=ttl,
        )
        await client.sadd(f"journey:{journey.id}:participants", str(participant.id))  # type: ignore[misc,attr-defined]
        await client.expire(f"journey:{journey.id}:participants", ttl)  # type: ignore[misc,attr-defined]
    except Exception:
        # Redis unavailable — Postgres still holds latest state; degraded mode.
        logger.warning("redis_live_state_unavailable")

    return sequence
