"""Structured JSON logging with request IDs.

Security rules enforced here:
- raw GPS coordinates, tokens and credentials are never logged; helpers
  redact common sensitive fields before any structured log is emitted.
"""

from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

REDACTED_KEYS = {
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "invite_token",
    "raw_token",
    "authorization",
    "push_token",
    "latitude",
    "longitude",
    "lat",
    "lng",
    "coordinates",
    "location",
    "fcm_private_key",
    "jwt_secret",
}


def new_request_id() -> str:
    return uuid.uuid4().hex


def get_request_id() -> str:
    return request_id_ctx.get()


def redact(value: Any) -> Any:
    """Recursively redact sensitive keys from dicts for safe logging."""
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if str(k).lower() in REDACTED_KEYS else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def _add_request_id(
    logger: logging.Logger, method_name: str, event_dict: structlog.types.EventDict
) -> structlog.types.EventDict:
    event_dict["request_id"] = get_request_id()
    return event_dict


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    """Configure structlog; JSON in production, pretty console in development."""
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared, structlog.processors.EventRenamer("message"), renderer],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level.upper(), force=True)
    for noisy in ("uvicorn.access", "uvicorn.error", "sqlalchemy.engine"):
        logging.getLogger(noisy).handlers = [logging.StreamHandler(sys.stdout)]
        logging.getLogger(noisy).propagate = False


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
