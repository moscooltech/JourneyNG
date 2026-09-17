"""Notification service: in-app records + FCM push abstraction.

Push payloads never contain raw GPS. FCM is optional — when credentials are
absent, notifications are recorded in-app only.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.logging import get_logger
from app.models.notification import Notification

logger = get_logger(__name__)


class PushProvider:
    """Abstraction; FCM implementation activates only when credentials exist."""

    async def send(self, user_id: str, title: str, body: str, data: dict | None = None) -> bool:
        settings = get_settings()
        if not settings.fcm_project_id:
            return False  # Development/no-FCM mode: in-app records only.
        try:
            from app.infrastructure.fcm import send_fcm_push

            return await send_fcm_push(user_id, title, body, data or {})
        except Exception:
            logger.warning("fcm_push_failed", user_id=user_id)
            return False


push_provider = PushProvider()


async def create_notification(
    db: AsyncSession,
    user_id,
    type_: str,
    title: str,
    body: str,
    data: dict | None = None,
    push: bool = True,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        type=type_,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(notification)
    await db.flush()
    if push:
        await push_provider.send(str(user_id), title, body, data)
    return notification
