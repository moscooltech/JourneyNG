"""Latest known location per participant (temporary, minimal retention)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import FLOAT, BigInteger, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LocationLatest(TimestampMixin, Base):
    __tablename__ = "location_latest"

    participant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("journey_participants.id"),
        primary_key=True,
    )
    journey_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("journeys.id"), nullable=False, index=True
    )
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6), nullable=False)
    accuracy_m: Mapped[float | None] = mapped_column(FLOAT)
    speed_mps: Mapped[float | None] = mapped_column(FLOAT)
    heading: Mapped[float | None] = mapped_column(FLOAT)
    altitude_m: Mapped[float | None] = mapped_column(FLOAT)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    server_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
