"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import auth, health, invitations, journeys, locations, participants, privacy, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(journeys.router)
api_router.include_router(invitations.router)
api_router.include_router(participants.router)
api_router.include_router(locations.router)
api_router.include_router(privacy.router)
