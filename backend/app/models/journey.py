"""Journey model and status state machine."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

JOURNEY_STATUSES = ("DRAFT", "INVITED", "ACTIVE", "COMPLETED", "CANCELLED", "EXPIRED")

# Journey state machine (spec §9)
JOURNEY_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"INVITED"},
    "INVITED": {"ACTIVE", "CANCELLED", "EXPIRED"},
    "ACTIVE": {"COMPLETED", "CANCELLED", "EXPIRED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
    "EXPIRED": set(),
}


def can_transition(current: str, target: str) -> bool:
    return target in JOURNEY_TRANSITIONS.get(current, set())


class Journey(TimestampMixin, Base):
    __tablename__ = "journeys"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    destination_name: Mapped[str | None] = mapped_column(Text)
    destination_lat: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    destination_lng: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="INVITED", nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    participants: Mapped[list[JourneyParticipant]] = relationship(
        "JourneyParticipant",
        back_populates="journey",
        cascade="all, delete-orphan",
    )
    invitations: Mapped[list[JourneyInvitation]] = relationship(
        "JourneyInvitation", back_populates="journey", cascade="all, delete-orphan"
    )


from app.models.invitation import JourneyInvitation  # noqa: E402, F401
from app.models.participant import JourneyParticipant  # noqa: E402, F401
