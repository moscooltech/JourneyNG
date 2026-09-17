"""Redis client (Valkey-compatible) for live state and rate limiting."""

from __future__ import annotations

import redis.asyncio as redis

from app.config.settings import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()  # type: ignore[attr-defined]
        _client = None
