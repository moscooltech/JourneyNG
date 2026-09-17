"""State machine helpers shared by services (spec §9)."""

from __future__ import annotations

from app.core.errors import AppError, ErrorCode
from app.models.journey import can_transition
from app.models.participant import participant_can_transition


def require_journey_transition(current: str, target: str) -> None:
    if not can_transition(current, target):
        raise AppError(
            ErrorCode.JOURNEY_INVALID_TRANSITION,
            f"Cannot move journey from {current} to {target}.",
        )


def require_participant_transition(current: str, target: str) -> None:
    if not participant_can_transition(current, target):
        raise AppError(
            ErrorCode.PARTICIPANT_INVALID_TRANSITION,
            f"Cannot move participant from {current} to {target}.",
        )
