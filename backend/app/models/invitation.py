"""Journey invitation model."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import ensure_utc
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.journey import Journey


class JourneyInvitation(TimestampMixin, Base):
    __tablename__ = "journey_invitations"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("journeys.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    max_uses: Mapped[int | None] = mapped_column(Integer)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    journey: Mapped[Journey] = relationship("Journey", back_populates="invitations")

    @property
    def is_usable(self) -> bool:
        if self.revoked_at is not None or ensure_utc(self.expires_at) < datetime.now(UTC):
            return False
        return not self.is_exhausted

    @property
    def is_exhausted(self) -> bool:
        return self.max_uses is not None and self.use_count >= self.max_uses
