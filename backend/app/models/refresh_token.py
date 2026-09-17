"""Refresh token model (hashes only, never raw tokens)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutils import ensure_utc
from app.models.base import Base, TimestampMixin


class RefreshToken(TimestampMixin, Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_from: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True))

    user: Mapped[User] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and ensure_utc(self.expires_at) > datetime.now(UTC)


from app.models.user import User  # noqa: E402, F401
