from __future__ import annotations

import structlog
from fastapi import WebSocket

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self._connections.setdefault(user_id, []).append(websocket)
        logger.info("ws_connected", user_id=user_id, total=self.connection_count)

    def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        user_sockets = self._connections.get(user_id, [])
        if websocket in user_sockets:
            user_sockets.remove(websocket)
        if not user_sockets:
            self._connections.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id, total=self.connection_count)

    async def send_json(self, data: dict, websocket: WebSocket) -> None:
        try:
            await websocket.send_json(data)
        except Exception as exc:
            logger.error("ws_send_failed", error=str(exc))

    async def broadcast_to_user(self, data: dict, user_id: str) -> None:
        for ws in self._connections.get(user_id, []):
            await self.send_json(data, ws)

    @property
    def connection_count(self) -> int:
        return sum(len(sockets) for sockets in self._connections.values())


manager = ConnectionManager()
