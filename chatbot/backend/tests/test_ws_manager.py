"""Tests for ConnectionManager — WebSocket registry."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.ws_manager import ConnectionManager


def _mock_ws() -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.fixture
def manager():
    return ConnectionManager()


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_accepts_websocket(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "user_1")
        ws.accept.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_connect_registers_connection(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "user_1")
        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_multiple_sockets_same_user(self, manager):
        ws1, ws2 = _mock_ws(), _mock_ws()
        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_1")
        assert manager.connection_count == 2

    @pytest.mark.asyncio
    async def test_connect_multiple_users(self, manager):
        ws1, ws2 = _mock_ws(), _mock_ws()
        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_2")
        assert manager.connection_count == 2


class TestDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "user_1")
        manager.disconnect(ws, "user_1")
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_removes_user_entry_when_empty(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "user_1")
        manager.disconnect(ws, "user_1")
        assert "user_1" not in manager._connections

    @pytest.mark.asyncio
    async def test_disconnect_leaves_other_sockets_intact(self, manager):
        ws1, ws2 = _mock_ws(), _mock_ws()
        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_1")
        manager.disconnect(ws1, "user_1")
        assert manager.connection_count == 1

    def test_disconnect_unknown_user_is_safe(self, manager):
        ws = _mock_ws()
        manager.disconnect(ws, "unknown_user")  # must not raise
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_already_removed_socket_is_safe(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "user_1")
        manager.disconnect(ws, "user_1")
        manager.disconnect(ws, "user_1")  # second call must not raise


class TestSendJson:
    @pytest.mark.asyncio
    async def test_send_json_calls_websocket_send_json(self, manager):
        ws = _mock_ws()
        await manager.send_json({"type": "pong"}, ws)
        ws.send_json.assert_awaited_once_with({"type": "pong"})

    @pytest.mark.asyncio
    async def test_send_json_suppresses_exceptions(self, manager):
        ws = _mock_ws()
        ws.send_json = AsyncMock(side_effect=RuntimeError("broken pipe"))
        await manager.send_json({"type": "test"}, ws)  # must not raise


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_user_sockets(self, manager):
        ws1, ws2 = _mock_ws(), _mock_ws()
        await manager.connect(ws1, "user_1")
        await manager.connect(ws2, "user_1")
        await manager.broadcast_to_user({"type": "delta", "content": "hi"}, "user_1")
        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_to_unknown_user_is_safe(self, manager):
        await manager.broadcast_to_user({"type": "ping"}, "nonexistent")  # must not raise


class TestConnectionCount:
    @pytest.mark.asyncio
    async def test_connection_count_zero_initially(self, manager):
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_count_increments_on_connect(self, manager):
        ws1 = _mock_ws()
        ws2 = _mock_ws()
        await manager.connect(ws1, "u1")
        assert manager.connection_count == 1
        await manager.connect(ws2, "u2")
        assert manager.connection_count == 2

    @pytest.mark.asyncio
    async def test_connection_count_decrements_on_disconnect(self, manager):
        ws = _mock_ws()
        await manager.connect(ws, "u1")
        manager.disconnect(ws, "u1")
        assert manager.connection_count == 0
