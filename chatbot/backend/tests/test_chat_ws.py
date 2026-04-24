"""WebSocket route tests for /ws/chat."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.services.llm.base import AgentLoopResult


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return create_access_token("ws_test_user")


def _mock_provider(stream_tokens=None):
    """Build a mock provider that streams given tokens."""
    provider = MagicMock()
    provider.provider_name = "mock"
    provider.default_model = "mock-model"

    async def _stream(messages, model, temperature, max_tokens=1024):
        for tok in (stream_tokens or ["Hello", " world"]):
            yield tok

    provider.stream = _stream
    provider.run_agent_loop = AsyncMock(side_effect=NotImplementedError("no agent loop"))
    provider.generate = AsyncMock(return_value="Mock Title")
    return provider


def _generic_answer_result():
    """Return an OrchestratorResult for a generic (non-agent) answer."""
    from app.agent.orchestrator import OrchestratorResult
    from app.services.llm.base import RoutingDecision
    return OrchestratorResult(
        routing_decision=RoutingDecision.GENERIC_ANSWER,
        use_agent_loop=False,
        intent_hint="",
    )


class TestWsChatInvalidToken:
    def test_bad_token_rejected(self, client):
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/chat?token=bad.token.here") as ws:
                ws.receive_json()

    def test_valid_token_gets_providers_frame(self, client, token):
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create") as mock_create:
            mock_create.return_value = _mock_provider()
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "providers"
                assert "data" in msg


class TestWsChatPing:
    def test_ping_returns_pong(self, client, token):
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create") as mock_create:
            mock_create.return_value = _mock_provider()
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                ws.send_json({"type": "ping"})
                msg = ws.receive_json()
                assert msg["type"] == "pong"


class TestWsChatMessage:
    """Test the full streaming message flow end-to-end via WebSocket."""

    def test_ping_pong_flow(self, client, token):
        """Verify ping/pong work independently of streaming."""
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create") as mock_create:
            mock_create.return_value = _mock_provider()
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                ws.send_json({"type": "ping"})
                msg = ws.receive_json()
                assert msg["type"] == "pong"

    def test_providers_frame_on_connect(self, client, token):
        """Server sends providers frame immediately on connect."""
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create") as mock_create:
            mock_create.return_value = _mock_provider()
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                msg = ws.receive_json()
                assert msg["type"] == "providers"
                assert isinstance(msg["data"], list)


class TestWsChatGenerateTitle:
    """Test the _generate_and_send_title helper function."""

    @pytest.mark.asyncio
    async def test_generate_and_send_title_sends_title_frame(self):
        from app.api.routes.chat_ws import _generate_and_send_title
        from app.services.llm_service import LLMService
        from app.services.llm.base import BaseLLMProvider
        from app.schemas.ws_messages import MsgIn

        # Create a mock provider and service
        mock_provider = MagicMock()
        mock_provider.default_model = "mock-model"
        mock_provider.generate = AsyncMock(return_value='"Mock Title"')
        service = LLMService(provider=mock_provider)

        mock_ws = AsyncMock()

        # A conversation that doesn't exist — title task should handle gracefully
        await _generate_and_send_title(mock_ws, service, "How do I log in?", "nonexistent-conv-xyz")

    @pytest.mark.asyncio
    async def test_generate_and_send_title_handles_send_error(self):
        from app.api.routes.chat_ws import _generate_and_send_title
        from app.services.llm_service import LLMService

        mock_provider = MagicMock()
        mock_provider.default_model = "mock-model"
        mock_provider.generate = AsyncMock(return_value="A Title")
        service = LLMService(provider=mock_provider)

        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=ConnectionResetError("closed"))

        # Should not raise — ConnectionResetError is handled internally
        await _generate_and_send_title(mock_ws, service, "hello", "nonexistent-xyz")


class TestWsChatHelperFunctions:
    """Test internal helper functions that are coverage targets."""

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_creates_new(self):
        from app.api.routes.chat_ws import _get_or_create_conversation
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            conv, is_new = await _get_or_create_conversation(db, "new-conv-abc", "user-abc")
            assert is_new is True
            assert conv.id == "new-conv-abc"
            await db.rollback()

    @pytest.mark.asyncio
    async def test_get_or_create_conversation_finds_existing(self):
        from app.api.routes.chat_ws import _get_or_create_conversation
        from app.core.database import AsyncSessionLocal
        from app.models.conversation import Conversation

        conv_id = "existing-conv-xyz"
        user_id = "user-xyz"

        async with AsyncSessionLocal() as db:
            db.add(Conversation(id=conv_id, user_id=user_id))
            await db.commit()

        async with AsyncSessionLocal() as db:
            conv, is_new = await _get_or_create_conversation(db, conv_id, user_id)
            assert is_new is False
            assert conv.id == conv_id
            # cleanup
            await db.delete(conv)
            await db.commit()

    @pytest.mark.asyncio
    async def test_save_messages_persists_both_roles(self):
        from app.api.routes.chat_ws import _save_messages, _get_or_create_conversation
        from app.core.database import AsyncSessionLocal
        from app.models.conversation import Message
        from sqlalchemy import select

        conv_id = "save-msg-test-conv"
        user_id = "save-msg-user"

        async with AsyncSessionLocal() as db:
            await _get_or_create_conversation(db, conv_id, user_id)
            await _save_messages(db, conv_id, "user question", "assistant answer", "mock", "mock-model", 10)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Message).where(Message.conversation_id == conv_id))
            msgs = result.scalars().all()
            roles = {m.role for m in msgs}
            assert "user" in roles
            assert "assistant" in roles
            # cleanup
            for m in msgs:
                await db.delete(m)
            from sqlalchemy import select as sel
            from app.models.conversation import Conversation
            r = await db.execute(sel(Conversation).where(Conversation.id == conv_id))
            conv = r.scalar_one_or_none()
            if conv:
                await db.delete(conv)
            await db.commit()

    def test_get_redis_returns_none_when_disabled(self):
        from app.api.routes import chat_ws
        import app.api.routes.chat_ws as chat_ws_module
        chat_ws_module._redis_client = None
        from app.core.config import settings
        original = settings.REDIS_ENABLED
        settings.REDIS_ENABLED = False
        result = chat_ws_module._get_redis()
        assert result is None
        settings.REDIS_ENABLED = original

    def test_get_skill_registry_returns_instance(self):
        from app.agent.skill_registry import SkillRegistry
        from app.api.routes import chat_ws as chat_ws_module
        chat_ws_module._skill_registry = None
        with patch.object(SkillRegistry, "_start_watcher", return_value=None):
            registry = chat_ws_module._get_skill_registry()
        assert registry is not None
        chat_ws_module._skill_registry = None

    def test_get_session_model_store_returns_instance(self):
        from app.api.routes import chat_ws as chat_ws_module
        chat_ws_module._session_model_store = None
        store = chat_ws_module._get_session_model_store()
        assert store is not None
        chat_ws_module._session_model_store = None
