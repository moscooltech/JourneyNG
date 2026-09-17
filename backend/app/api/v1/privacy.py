"""Privacy endpoints (spec §11.7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthenticatedError
from app.infrastructure.database import get_db
from app.security.authorization import Requester, get_requester
from app.services import privacy_service

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/active-sharing")
async def active_sharing(
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if requester.user is None:
        raise UnauthenticatedError()
    return await privacy_service.active_sharing_for_user(db, requester.user.id)


@router.post("/stop-all-sharing")
async def stop_all(
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if requester.user is None:
        raise UnauthenticatedError()
    count = await privacy_service.stop_all_sharing(db, requester.user.id)
    return {"revoked": count}
