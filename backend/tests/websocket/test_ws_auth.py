"""WebSocket tests: connection auth and snapshot shape (unit-level parts)."""

from __future__ import annotations

from app.websocket.manager import Connection, ConnectionManager


class TestConnectionManager:
    def test_disconnect_removes_connection(self):
        mgr = ConnectionManager()
        conn = Connection(
            websocket=None,  # type: ignore[arg-type]
            journey_id="j1",
            viewer_user_id="u1",
            viewer_guest_session_id=None,
        )
        mgr._channels["j1"].append(conn)
        mgr.disconnect(conn)
        assert "j1" not in mgr._channels

    def test_authorized_connections_scoped(self):
        mgr = ConnectionManager()
        conn = Connection(
            websocket=None,  # type: ignore[arg-type]
            journey_id="j1",
            viewer_user_id="host1",
            viewer_guest_session_id=None,
            authorized_participant_ids={"p1", "p2"},
        )
        mgr._channels["j1"].append(conn)

        assert mgr.authorized_connections("j1", "p1") == [conn]
        assert mgr.authorized_connections("j1", "p3") == []
        assert mgr.authorized_connections("j2", "p1") == []
