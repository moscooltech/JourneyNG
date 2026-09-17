"""Models package: imports all models so Base.metadata is complete."""

from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.consent import LocationConsent  # noqa: F401
from app.models.device import Device  # noqa: F401
from app.models.guest_session import GuestSession  # noqa: F401
from app.models.invitation import JourneyInvitation  # noqa: F401
from app.models.journey import Journey  # noqa: F401
from app.models.location_latest import LocationLatest  # noqa: F401
from app.models.notification import Notification  # noqa: F401
from app.models.participant import JourneyParticipant  # noqa: F401
from app.models.privacy_settings import PrivacySettings  # noqa: F401
from app.models.profile import Profile  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.user import User  # noqa: F401
