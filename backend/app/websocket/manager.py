"""WebSocket connection manager.

Every connection is authenticated and authorized for a specific journey
channel before any event is delivered. Broadcasts are per-recipient
authorized: a participant's location is only sent to viewers with access.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from fastapi import WebSocket


@dataclass
class Connection:
    websocket: WebSocket
    journey_id: str
    viewer_user_id: str | None
    viewer_guest_session_id: str | None
    # Locations this connection is authorized to receive (participant_ids).
    authorized_participant_ids: set[str] = field(default_factory=set)
    # Host connections may receive all consented participant locations.
    is_host: bool = False


class ConnectionManager:
    def __init__(self) -> None:
        self._channels: dict[str, list[Connection]] = defaultdict(list)

    async def connect(self, conn: Connection) -> None:
        await conn.websocket.accept()
        self._channels[conn.journey_id].append(conn)

    def disconnect(self, conn: Connection) -> None:
        channel = self._channels.get(conn.journey_id, [])
        if conn in channel:
            channel.remove(conn)
        if not channel and conn.journey_id in self._channels:
            del self._channels[conn.journey_id]

    def authorized_connections(self, journey_id: str, participant_id: str) -> list[Connection]:
        """Connections allowed to see a given participant's location."""
        result = []
        for conn in self._channels.get(journey_id, []):
            if conn.is_host or participant_id in conn.authorized_participant_ids:
                result.append(conn)
        return result

    async def broadcast_to_authorized(
        self, journey_id: str, participant_id: str, payload: dict
    ) -> None:
        import json

        text = json.dumps(payload)
        for conn in self.authorized_connections(journey_id, participant_id):
            try:
                await conn.websocket.send_text(text)
            except Exception:
                self.disconnect(conn)

    async def broadcast_to_channel(self, journey_id: str, payload: dict) -> None:
        """Journey-level events (started/completed/cancelled/expired) — safe for all members."""
        import json

        text = json.dumps(payload)
        for conn in list(self._channels.get(journey_id, [])):
            try:
                await conn.websocket.send_text(text)
            except Exception:
                self.disconnect(conn)

    def channel_size(self, journey_id: str) -> int:
        return len(self._channels.get(journey_id, []))


manager = ConnectionManager()
