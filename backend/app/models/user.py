"""User model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, PKUUIDMixin, TimestampMixin

USER_STATUSES = ("ACTIVE", "SUSPENDED", "DELETED")


class User(PKUUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_provider: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE", nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    profile: Mapped[Profile | None] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    devices: Mapped[list[Device]] = relationship(
        "Device", back_populates="user", cascade="all, delete-orphan"
    )


from app.models.device import Device  # noqa: E402, F401
from app.models.profile import Profile  # noqa: E402, F401
from app.models.refresh_token import RefreshToken  # noqa: E402, F401
