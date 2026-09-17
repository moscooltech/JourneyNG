"""User profile endpoints (spec §11.1): GET/PATCH/DELETE /me."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthenticatedError
from app.infrastructure.database import get_db
from app.models.journey import Journey
from app.schemas.auth import ProfileUpdateRequest, UserOut
from app.security.authorization import Requester, get_requester
from app.services import auth_service

router = APIRouter(tags=["users"])


def _user_out(requester: Requester) -> UserOut:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    return UserOut(
        id=user.id,
        email=user.email,
        phone=user.phone,
        status=user.status,
        display_name=user.profile.display_name if user.profile else None,
        created_at=user.created_at,
    )


@router.get("/me", response_model=UserOut)
async def get_me(requester: Requester = Depends(get_requester)) -> UserOut:
    return _user_out(requester)


@router.patch("/me", response_model=UserOut)
async def update_me(
    req: ProfileUpdateRequest,
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    user = requester.user
    if user is None:
        raise UnauthenticatedError()
    if user.profile is not None:
        if req.display_name is not None:
            user.profile.display_name = req.display_name
        if req.photo_url is not None:
            user.profile.photo_url = req.photo_url
    await db.flush()
    return _user_out(requester)


@router.delete("/me", status_code=202)
async def delete_me(
    requester: Requester = Depends(get_requester),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Account deletion workflow (spec §30). 202 = accepted."""
    user = requester.user
    if user is None:
        raise UnauthenticatedError()

    # Terminate active journeys hosted by this user.
    journeys = (
        await db.execute(
            select(Journey).where(
                Journey.host_user_id == user.id,
                Journey.status.in_(["INVITED", "ACTIVE"]),
            )
        )
    ).scalars()
    for j in journeys:
        j.status = "CANCELLED"
        j.completed_at = datetime.now(UTC)

    # Revoke sharing and sessions.
    from app.services.privacy_service import stop_all_sharing

    await stop_all_sharing(db, user.id)
    await auth_service.revoke_all_sessions(db, user.id)

    # Anonymize account per retention rules (spec §29/30).
    user.status = "DELETED"
    if user.profile:
        user.profile.display_name = "Deleted User"
        user.profile.photo_url = None
    user.email = None
    user.phone = None
    user.password_hash = None
    await db.flush()
    return {"status": "deletion_accepted"}
