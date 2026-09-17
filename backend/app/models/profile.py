"""Profile model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship("User", back_populates="profile")


from app.models.user import User  # noqa: E402, F401
