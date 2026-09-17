"""Health and readiness endpoints (spec §36)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy import text

from app.config.settings import settings
from app.infrastructure.database import get_engine
from app.infrastructure.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}


@router.get("/ready")
async def ready(response: Response) -> dict:
    """Readiness: verifies Postgres and Redis connectivity, reports degraded state."""
    components: dict[str, str] = {}
    healthy = True

    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        components["postgres"] = "ok"
    except Exception:
        components["postgres"] = "unavailable"
        healthy = False

    try:
        client = get_redis()
        await client.ping()
        components["redis"] = "ok"
    except Exception:
        components["redis"] = "degraded"
        # Redis loss degrades live features but the API can still serve.

    if not healthy:
        response.status_code = 503
    return {"status": "ok" if healthy else "degraded", "components": components}
