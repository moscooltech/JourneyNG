"""Location validation tests (spec §32)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import AppError
from app.services.location_service import validate_coordinates, validate_timestamp


class TestCoordinateValidation:
    def test_valid_lagos_coordinates(self):
        validate_coordinates(6.5244, 3.3792, 8.2)

    def test_latitude_out_of_range(self):
        with pytest.raises(AppError):
            validate_coordinates(91.0, 3.3792, 8.2)

    def test_longitude_out_of_range(self):
        with pytest.raises(AppError):
            validate_coordinates(6.5244, 181.0, 8.2)

    def test_nan_rejected(self):
        with pytest.raises(AppError):
            validate_coordinates(float("nan"), 3.3792, 8.2)

    def test_poor_accuracy_rejected(self):
        with pytest.raises(AppError):
            validate_coordinates(6.5244, 3.3792, 500.0)


class TestTimestampValidation:
    def test_recent_timestamp_accepted(self):
        validate_timestamp(datetime.now(UTC) - timedelta(seconds=5))

    def test_future_timestamp_rejected(self):
        with pytest.raises(AppError):
            validate_timestamp(datetime.now(UTC) + timedelta(minutes=10))

    def test_very_old_timestamp_rejected(self):
        with pytest.raises(AppError):
            validate_timestamp(datetime.now(UTC) - timedelta(hours=2))
