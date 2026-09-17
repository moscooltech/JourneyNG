"""Datetime helpers.

SQLite (used in the test suite) returns naive datetimes; Postgres returns
aware ones. All in-process comparisons must normalize first.
"""

from __future__ import annotations

from datetime import UTC, datetime


def ensure_utc(dt: datetime) -> datetime:
    """Returns a timezone-aware UTC datetime."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def utc_now() -> datetime:
    return datetime.now(UTC)
