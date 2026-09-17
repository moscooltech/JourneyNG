"""Location consent model — treated as authorization state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import ensure_utc
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.participant import JourneyParticipant

CONSENT_PURPOSES = ("TRAVEL_TO_DESTINATION",)
CONSENT_SCOPES = ("LIVE_LOCATION",)
CONSENT_STATUSES = ("GRANTED", "REVOKED", "EXPIRED")


class LocationConsent(TimestampMixin, Base):
    __tablename__ = "location_consents"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("journeys.id"), nullable=False, index=True
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("journey_participants.id"),
        nullable=False,
        index=True,
    )
    viewer_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consent_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1")

    participant: Mapped[JourneyParticipant] = relationship(
        "JourneyParticipant", back_populates="consents"
    )

    @property
    def is_active(self) -> bool:
        return self.status == "GRANTED" and ensure_utc(self.expires_at) > datetime.now(UTC)
