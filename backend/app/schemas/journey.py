"""Journey, participant, consent and location schemas."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DestinationIn(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)


class JourneyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: DestinationIn
    expires_in_minutes: int = Field(default=120, ge=15, le=1440)


class InvitationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_uses: int | None = Field(default=None, ge=1, le=100)
    expires_in_minutes: int = Field(default=120, ge=5, le=1440)


class ConsentGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope: str = "LIVE_LOCATION"
    purpose: str = "TRAVEL_TO_DESTINATION"
    duration: str = "UNTIL_ARRIVAL"


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    purpose: str
    scope: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    viewer_user_id: UUID


class LocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    speed_mps: float | None = Field(default=None, ge=0, le=200)
    heading: float | None = Field(default=None, ge=0, le=360)
    altitude_m: float | None = Field(default=None, ge=-1000, le=10000)
    recorded_at: datetime


class LocationAccepted(BaseModel):
    accepted: bool
    server_received_at: datetime
    server_sequence: int


class GuestJoin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=64)


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    status: str
    display_name: str
    user_id: UUID | None = None
    joined_at: datetime | None
    left_at: datetime | None


class JourneyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    destination_name: str | None
    destination_lat: Decimal
    destination_lng: Decimal
    started_at: datetime | None
    expires_at: datetime
    completed_at: datetime | None
    created_at: datetime


class JourneyDetail(BaseModel):
    journey: JourneyOut
    participants: list[ParticipantOut]
    viewer_role: str
    is_host: bool
