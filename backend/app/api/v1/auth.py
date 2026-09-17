"""Auth API endpoints (spec §11.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import get_db
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.security.rate_limit import enforce_rate_limit
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    await enforce_rate_limit("register", request.client.host if request.client else "unknown", 5)
    user, access, refresh = await auth_service.register_user(db, req)
    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            phone=user.phone,
            status=user.status,
            display_name=req.display_name,
            created_at=user.created_at,
        ),
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    await enforce_rate_limit("login", req.identifier.lower(), 10)
    user, access, refresh = await auth_service.login(db, req.identifier, req.password)
    display_name = user.profile.display_name if user.profile else ""
    return AuthResponse(
        user=UserOut(
            id=user.id,
            email=user.email,
            phone=user.phone,
            status=user.status,
            display_name=display_name,
            created_at=user.created_at,
        ),
        access_token=access,
        refresh_token=refresh,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    user, access, new_refresh = await auth_service.rotate_refresh_token(db, req.refresh_token)
    return TokenPair(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=204)
async def logout(
    req: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    await auth_service.logout(db, req.refresh_token)
