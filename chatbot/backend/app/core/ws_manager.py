from __future__ import annotations

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    """In-process registry of active WebSocket connections, keyed by user ID.

    One user may hold multiple simultaneous connections (e.g. multiple browser tabs).
    All send operations silently log errors so a broken socket never raises and
    disrupts other connections.
    """

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            websocket: Incoming WebSocket to accept.
            user_id: Authenticated user owning this connection.
        """
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info("ws_connected", user_id=user_id, total=self.connection_count)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a WebSocket from the registry.

        Cleans up the user entry entirely when no sockets remain. Safe to call
        after a disconnect even if the socket was already removed.

        Args:
            websocket: The socket that disconnected.
            user_id: Owner of the disconnected socket.
        """
        user_sockets = self._connections.get(user_id, [])
        if websocket in user_sockets:
            user_sockets.remove(websocket)
        if not user_sockets:
            self._connections.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id, total=self.connection_count)

    async def send_json(self, data: dict, websocket: WebSocket) -> None:
        """Send a JSON frame to a specific WebSocket.

        Errors are logged and suppressed so a broken socket does not raise into
        the caller. The frame is silently discarded if the send fails.

        Args:
            data: JSON-serialisable dict to send.
            websocket: Target WebSocket.
        """
        try:
            await websocket.send_json(data)
        except Exception as exc:
            logger.error("ws_send_failed", error=str(exc))

    async def broadcast_to_user(self, data: dict, user_id: str) -> None:
        """Send a JSON frame to all sockets belonging to a user.

        Args:
            data: JSON-serialisable dict to send.
            user_id: Target user. No-op if the user has no active connections.
        """
        for ws in self._connections.get(user_id, []):
            await self.send_json(data, ws)

    @property
    def connection_count(self) -> int:
        """Total number of active WebSocket connections across all users."""
        return sum(len(sockets) for sockets in self._connections.values())


manager = ConnectionManager()
