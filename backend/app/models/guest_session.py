"""Guest session model — scoped to a single journey."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.timeutils import ensure_utc
from app.models.base import Base, TimestampMixin

GUEST_STATUSES = ("ACTIVE", "EXPIRED", "REVOKED", "COMPLETED")


class GuestSession(TimestampMixin, Base):
    __tablename__ = "guest_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("journeys.id"), nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def is_expired(self) -> bool:
        return ensure_utc(self.expires_at) < datetime.now(UTC)
