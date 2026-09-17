"""Privacy settings model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PrivacySettings(TimestampMixin, Base):
    __tablename__ = "privacy_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    analytics_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    personalization_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
