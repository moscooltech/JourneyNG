"""Expiry worker: expires journeys and consents (spec §35)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from sqlalchemy import select

from app.config.settings import settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.database import get_sessionmaker
from app.models.consent import LocationConsent
from app.models.journey import Journey

logger = get_logger(__name__)


async def expire_journeys(db) -> int:
    now = datetime.now(UTC)
    journeys = (
        await db.execute(
            select(Journey).where(
                Journey.status.in_(["INVITED", "ACTIVE"]),
                Journey.expires_at <= now,
            )
        )
    ).scalars()
    count = 0
    for journey in journeys:
        journey.status = "EXPIRED"
        count += 1
    await db.flush()
    return count


async def expire_participants_of_expired_journeys(db) -> int:
    now = datetime.now(UTC)
    expired = (
        await db.execute(
            select(Journey).where(
                Journey.status == "EXPIRED",
                Journey.updated_at >= now - __import__("datetime").timedelta(minutes=10),
            )
        )
    ).scalars()
    count = 0
    for journey in expired:
        for p in journey.participants:
            if p.status in ("INVITED", "ACCEPTED", "ACTIVE"):
                p.status = "EXPIRED"
                count += 1
    await db.flush()
    return count


async def expire_consents(db) -> int:
    now = datetime.now(UTC)
    consents = (
        await db.execute(
            select(LocationConsent).where(
                LocationConsent.status == "GRANTED",
                LocationConsent.expires_at <= now,
            )
        )
    ).scalars()
    count = 0
    for consent in consents:
        consent.status = "EXPIRED"
        count += 1
    await db.flush()
    return count


async def run_once() -> dict:
    session_factory = get_sessionmaker()
    async with session_factory() as db:
        journeys = await expire_journeys(db)
        participants = await expire_participants_of_expired_journeys(db)
        consents = await expire_consents(db)
        await db.commit()
    return {
        "journeys_expired": journeys,
        "participants_expired": participants,
        "consents_expired": consents,
    }


async def main(interval_seconds: int = 30) -> None:
    configure_logging(settings.log_level)
    logger.info("expiry_worker_started", interval=interval_seconds)
    while True:
        try:
            result = await run_once()
            if any(result.values()):
                logger.info("expiry_pass", **result)
        except Exception:
            logger.exception("expiry_worker_error")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
