"""Journey participant model and state machine."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.consent import LocationConsent
    from app.models.guest_session import GuestSession
    from app.models.journey import Journey

PARTICIPANT_ROLES = ("HOST", "VISITOR")

PARTICIPANT_STATUSES = (
    "INVITED",
    "ACCEPTED",
    "ACTIVE",
    "ARRIVED",
    "DECLINED",
    "LEFT",
    "REMOVED",
    "EXPIRED",
)

TERMINAL_STATUSES = {"DECLINED", "LEFT", "REMOVED", "EXPIRED"}

# Participant state machine (spec §9)
PARTICIPANT_TRANSITIONS: dict[str, set[str]] = {
    "INVITED": {"ACCEPTED", "DECLINED", "EXPIRED"},
    "ACCEPTED": {"ACTIVE", "LEFT"},
    "ACTIVE": {"ARRIVED", "LEFT", "REMOVED", "EXPIRED"},
    "ARRIVED": set(),
    "DECLINED": set(),
    "LEFT": set(),
    "REMOVED": set(),
    "EXPIRED": set(),
}


def participant_can_transition(current: str, target: str) -> bool:
    return target in PARTICIPANT_TRANSITIONS.get(current, set())


class JourneyParticipant(TimestampMixin, Base):
    __tablename__ = "journey_participants"
    __table_args__ = (
        CheckConstraint(
            "(user_id IS NOT NULL AND guest_session_id IS NULL) OR "
            "(user_id IS NULL AND guest_session_id IS NOT NULL)",
            name="participant_identity_xor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("journeys.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    guest_session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("guest_sessions.id"), nullable=True, index=True
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="INVITED", nullable=False)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    journey: Mapped[Journey] = relationship("Journey", back_populates="participants")
    guest_session: Mapped[GuestSession | None] = relationship("GuestSession")
    consents: Mapped[list[LocationConsent]] = relationship(
        "LocationConsent", back_populates="participant", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"
