"""Domain error taxonomy mapped to the spec's error envelope.

Error shape:
{
  "error": {"code": "...", "message": "...", "request_id": "..."}
}
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"

    # Auth
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    ACCOUNT_SUSPENDED = "ACCOUNT_SUSPENDED"
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    EMAIL_TAKEN = "EMAIL_TAKEN"
    PHONE_TAKEN = "PHONE_TAKEN"
    WEAK_PASSWORD = "WEAK_PASSWORD"  # noqa: S105
    INVALID_REFRESH_TOKEN = "INVALID_REFRESH_TOKEN"  # noqa: S105

    # Journey / participants
    JOURNEY_NOT_FOUND = "JOURNEY_NOT_FOUND"
    JOURNEY_NOT_ACTIVE = "JOURNEY_NOT_ACTIVE"
    JOURNEY_INVALID_TRANSITION = "JOURNEY_INVALID_TRANSITION"
    JOURNEY_EXPIRED = "JOURNEY_EXPIRED"
    PARTICIPANT_NOT_FOUND = "PARTICIPANT_NOT_FOUND"
    PARTICIPANT_INVALID_TRANSITION = "PARTICIPANT_INVALID_TRANSITION"
    PARTICIPANT_LIMIT_REACHED = "PARTICIPANT_LIMIT_REACHED"
    HOST_ONLY_ACTION = "HOST_ONLY_ACTION"

    # Invitations
    INVITATION_NOT_FOUND = "INVITATION_NOT_FOUND"
    INVITATION_EXPIRED = "INVITATION_EXPIRED"
    INVITATION_REVOKED = "INVITATION_REVOKED"
    INVITATION_EXHAUSTED = "INVITATION_EXHAUSTED"
    INVALID_INVITATION_TOKEN = "INVALID_INVITATION_TOKEN"  # noqa: S105

    # Guest
    GUEST_SESSION_INVALID = "GUEST_SESSION_INVALID"
    GUEST_SESSION_EXPIRED = "GUEST_SESSION_EXPIRED"

    # Consent / location
    CONSENT_REQUIRED = "CONSENT_REQUIRED"
    CONSENT_REVOKED = "CONSENT_REVOKED"
    CONSENT_NOT_FOUND = "CONSENT_NOT_FOUND"
    LOCATION_REJECTED = "LOCATION_REJECTED"
    LOCATION_UNAUTHORIZED = "LOCATION_UNAUTHORIZED"

    # Throttling
    RATE_LIMITED = "RATE_LIMITED"

    # Misc
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Base application error carrying a stable machine-readable code."""

    status_code = 400

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


class UnauthenticatedError(AppError):
    status_code = 401

    def __init__(
        self,
        message: str = "Authentication required.",
        code: ErrorCode = ErrorCode.UNAUTHENTICATED,
    ) -> None:
        super().__init__(code, message, 401)


class ForbiddenError(AppError):
    status_code = 403

    def __init__(
        self, message: str = "Not allowed.", code: ErrorCode = ErrorCode.FORBIDDEN
    ) -> None:
        super().__init__(code, message, 403)


class NotFoundError(AppError):
    status_code = 404

    def __init__(self, code: ErrorCode = ErrorCode.NOT_FOUND, message: str = "Not found.") -> None:
        super().__init__(code, message, 404)


class ConflictError(AppError):
    status_code = 409

    def __init__(self, code: ErrorCode, message: str) -> None:
        super().__init__(code, message, 409)


class RateLimitedError(AppError):
    status_code = 429

    def __init__(self, message: str = "Too many requests. Please retry later.") -> None:
        super().__init__(ErrorCode.RATE_LIMITED, message, 429)
