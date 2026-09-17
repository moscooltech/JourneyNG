"""Rate limiting: Redis-backed fixed window with in-memory fallback.

If Redis is unavailable the limiter degrades to per-process counting so the
API keeps operating (with weaker guarantees) instead of failing hard.
"""

from __future__ import annotations

import time
from collections import defaultdict

from app.core.errors import RateLimitedError
from app.infrastructure.redis import get_redis

_mem_buckets: dict[str, list[float]] = defaultdict(list)


def reset_inmemory_buckets() -> None:
    """Test hook: clears fallback buckets between tests."""
    _mem_buckets.clear()


async def enforce_rate_limit(scope: str, key: str, limit_per_min: int) -> None:
    """Raise RateLimitedError when `key` exceeds `limit_per_min` for `scope`."""
    redis_key = f"rate:{scope}:{key}"

    try:
        client = get_redis()
        now = time.time()
        async with client.pipeline(transaction=True) as pipe:
            await pipe.zremrangebyscore(redis_key, "-inf", now - 60.0)
            await pipe.zcard(redis_key)
            await pipe.zadd(redis_key, {f"{now}:{time.time_ns()}": now})
            await pipe.expire(redis_key, 90)
            results = await pipe.execute()
        count = int(results[1]) + 1
        if count > limit_per_min:
            raise RateLimitedError()
    except RateLimitedError:
        raise
    except Exception:
        # Redis unavailable: in-memory fallback (per-process only).
        cutoff = time.time() - 60.0
        bucket = [t for t in _mem_buckets[redis_key] if t > cutoff]
        bucket.append(time.time())
        _mem_buckets[redis_key] = bucket
        if len(bucket) > limit_per_min:
            raise RateLimitedError() from None
