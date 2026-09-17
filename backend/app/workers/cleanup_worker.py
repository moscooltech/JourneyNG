"""Cleanup worker: removes expired location data per retention policy (spec §29, §35)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app.config.settings import settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.database import get_sessionmaker
from app.models.location_latest import LocationLatest

logger = get_logger(__name__)


async def cleanup_location_data(db) -> int:
    """Deletes location rows older than the configured retention window."""
    cutoff = datetime.now(UTC) - timedelta(hours=settings.location_retention_hours)
    result = await db.execute(delete(LocationLatest).where(LocationLatest.received_at < cutoff))
    await db.flush()
    return result.rowcount or 0


async def cleanup_stale_redis_state() -> int:
    """Removes Redis journey participant sets for ended journeys (TTL is primary)."""
    try:
        from app.infrastructure.redis import get_redis

        client = get_redis()
        keys = []
        async for key in client.scan_iter(match="journey:*:participants", count=100):
            keys.append(key)
        cleaned = 0
        for key in keys:
            journey_id = key.split(":")[1]
            journey = None
            session_factory = get_sessionmaker()
            async with session_factory() as db:
                from app.models.journey import Journey

                journey = await db.get(Journey, journey_id)
            if journey is None or journey.status in ("COMPLETED", "CANCELLED", "EXPIRED"):
                await client.delete(key)
                cleaned += 1
        return cleaned
    except Exception:
        logger.warning("redis_cleanup_skipped")
        return 0


async def run_once() -> dict:
    session_factory = get_sessionmaker()
    async with session_factory() as db:
        locations = await cleanup_location_data(db)
        await db.commit()
    redis_cleaned = await cleanup_stale_redis_state()
    return {"locations_deleted": locations, "redis_keys_cleaned": redis_cleaned}


async def main(interval_seconds: int = 300) -> None:
    configure_logging(settings.log_level)
    logger.info("cleanup_worker_started", interval=interval_seconds)
    while True:
        try:
            result = await run_once()
            if any(result.values()):
                logger.info("cleanup_pass", **result)
        except Exception:
            logger.exception("cleanup_worker_error")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
