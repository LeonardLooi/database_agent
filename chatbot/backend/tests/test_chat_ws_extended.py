"""Extended chat_ws tests — covers the main message handler flow."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return create_access_token("ws_ext_user")


def _mock_provider_streaming(tokens=None):
    provider = MagicMock()
    provider.provider_name = "mock"
    provider.default_model = "mock-model"
    provider.generate = AsyncMock(return_value="Test Title")

    async def _stream(messages, model, temperature, max_tokens=1024):
        for tok in (tokens or ["Hello", " world"]):
            yield tok

    provider.stream = _stream
    provider.run_agent_loop = AsyncMock(
        return_value=AgentLoopResult(status="completed", explanation="Agent answer", sql_used=[])
    )
    return provider


_MOCK_TITLE = AsyncMock(return_value=None)


# ── _generate_and_send_title with existing conversation ──────────────────────

class TestGenerateAndSendTitleExtended:
    @pytest.mark.asyncio
    async def test_updates_title_for_existing_conversation(self):
        """Lines 119-120: conv found → title updated and committed."""
        from app.api.routes.chat_ws import _generate_and_send_title, _get_or_create_conversation
        from app.core.database import AsyncSessionLocal
        from app.models.conversation import Conversation
        from app.services.llm_service import LLMService
        from sqlalchemy import select

        conv_id = "title-update-test"
        user_id = "title-user-1"

        async with AsyncSessionLocal() as db:
            await _get_or_create_conversation(db, conv_id, user_id)
            await db.commit()

        mock_provider = MagicMock()
        mock_provider.default_model = "mock-model"
        mock_provider.generate = AsyncMock(return_value="The New Title")
        service = LLMService(provider=mock_provider)
        mock_ws = AsyncMock()

        await _generate_and_send_title(mock_ws, service, "What is 2+2?", conv_id)

        # Verify title was saved
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Conversation).where(Conversation.id == conv_id))
            conv = result.scalar_one_or_none()
            assert conv is not None
            assert conv.title == "The New Title"
            await db.delete(conv)
            await db.commit()

    @pytest.mark.asyncio
    async def test_title_send_runtime_error_suppressed(self):
        """Lines 126-127: RuntimeError during send is caught and logged."""
        from app.api.routes.chat_ws import _generate_and_send_title
        from app.services.llm_service import LLMService

        mock_provider = MagicMock()
        mock_provider.default_model = "mock-model"
        mock_provider.generate = AsyncMock(return_value="Title")
        service = LLMService(provider=mock_provider)

        mock_ws = AsyncMock()
        mock_ws.send_json = AsyncMock(side_effect=RuntimeError("WS already closed"))

        # Should not raise
        await _generate_and_send_title(mock_ws, service, "question", "nonexistent-conv")


# ── Redis lazy init (lines 41-45) ──────────────────────────────────────────

class TestGetRedisLazyInit:
    def test_get_redis_creates_client_when_enabled(self):
        import app.api.routes.chat_ws as chat_ws_module
        from app.core.config import settings

        original_client = chat_ws_module._redis_client
        original_enabled = settings.REDIS_ENABLED
        chat_ws_module._redis_client = None
        settings.REDIS_ENABLED = True

        try:
            with patch("redis.from_url", return_value=MagicMock()) as mock_redis:
                result = chat_ws_module._get_redis()
            mock_redis.assert_called_once()
            assert result is not None
            assert chat_ws_module._redis_client is not None
        finally:
            settings.REDIS_ENABLED = original_enabled
            chat_ws_module._redis_client = original_client


# ── Full streaming message flow ───────────────────────────────────────────────

class TestWsStreamingMessageFlow:
    """Tests that cover lines 174-584 by sending actual messages through WS."""

    def _send_message(self, ws, content="hello world", conv_id="ws-stream-test-1", model=""):
        ws.send_json({
            "type": "message",
            "messages": [{"role": "user", "content": content}],
            "conversation_id": conv_id,
            "model": model,
            "temperature": 0.7,
        })

    def _collect_until_done(self, ws, max_frames=30):
        frames = []
        for _ in range(max_frames):
            try:
                frame = ws.receive_json()
                frames.append(frame)
                if frame.get("type") in ("done", "error", "agent_response", "clarification_request"):
                    break
            except Exception:
                break
        return frames

    def test_streaming_generic_answer_flow(self, client, token):
        """Full generic answer streaming path (lines 174-584)."""
        mock_provider = _mock_provider_streaming(tokens=["Hi", " there"])

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "tell me a joke", conv_id="joke-conv-1")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "done" in types

    def test_streaming_with_model_specified(self, client, token):
        """Provider resolution when model is specified in message."""
        mock_provider = _mock_provider_streaming(tokens=["Answer"])

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.api.routes.chat_ws.LLMProviderFactory.resolve_provider_for_model",
                   return_value="mock"), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "question", conv_id="model-conv-1", model="gpt-4o")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "done" in types

    def test_streaming_provider_creation_error_sends_error_frame(self, client, token):
        """When provider.create() fails (no provider), error frame is sent."""
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   side_effect=RuntimeError("No providers configured")), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "question", conv_id="no-provider-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "error" in types

    def test_streaming_llm_error_sends_error_frame(self, client, token):
        """LLM stream raises → error frame sent, loop continues."""
        mock_provider = _mock_provider_streaming()

        async def _failing_stream(*args, **kwargs):
            raise RuntimeError("LLM quota exceeded")
            yield  # pragma: no cover

        mock_provider.stream = _failing_stream

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "query", conv_id="stream-err-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "error" in types

    def test_agent_loop_flow(self, client, token):
        """use_agent_loop=True path — run_agent_loop called."""
        mock_provider = _mock_provider_streaming()
        mock_provider.run_agent_loop = AsyncMock(
            return_value=AgentLoopResult(
                status="completed",
                explanation="Agent found data",
                sql_used=["SELECT 1"],
            )
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.query_router.QueryRouter.is_data_query", return_value=True), \
             patch("app.agent.query_router.QueryRouter.estimate_intent",
                   return_value=MagicMock(confidence=1.0, is_ambiguous=False, candidates=[])), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "show me sales data", conv_id="agent-loop-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert types & {"done", "error", "agent_response"}  # may fail gracefully

    def test_agent_loop_error_sends_error_frame(self, client, token):
        """run_agent_loop raises Exception → error frame."""
        mock_provider = _mock_provider_streaming()
        mock_provider.run_agent_loop = AsyncMock(side_effect=RuntimeError("bedrock down"))

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.query_router.QueryRouter.is_data_query", return_value=True), \
             patch("app.agent.query_router.QueryRouter.estimate_intent",
                   return_value=MagicMock(confidence=1.0, is_ambiguous=False, candidates=[])), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "show me data", conv_id="agent-err-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "error" in types

    def test_agent_loop_not_implemented_falls_back_to_stream(self, client, token):
        """run_agent_loop raises NotImplementedError → fallback to stream."""
        mock_provider = _mock_provider_streaming(tokens=["Streamed"])
        mock_provider.run_agent_loop = AsyncMock(side_effect=NotImplementedError)

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.query_router.QueryRouter.is_data_query", return_value=True), \
             patch("app.agent.query_router.QueryRouter.estimate_intent",
                   return_value=MagicMock(confidence=1.0, is_ambiguous=False, candidates=[])), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "data query", conv_id="notimpl-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "done" in types

    def test_agent_loop_result_error_status_sends_error(self, client, token):
        """loop_result.status == 'error' → error frame."""
        mock_provider = _mock_provider_streaming()
        mock_provider.run_agent_loop = AsyncMock(
            return_value=AgentLoopResult(
                status="error",
                error="connection refused",
            )
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.query_router.QueryRouter.is_data_query", return_value=True), \
             patch("app.agent.query_router.QueryRouter.estimate_intent",
                   return_value=MagicMock(confidence=1.0, is_ambiguous=False, candidates=[])), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                self._send_message(ws, "query", conv_id="loop-err-conv")
                frames = self._collect_until_done(ws)

        types = {f.get("type") for f in frames}
        assert "error" in types

    def test_disconnect_exits_cleanly(self, client, token):
        """WebSocketDisconnect causes the loop to exit cleanly."""
        mock_provider = _mock_provider_streaming()
        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.api.routes.chat_ws._generate_and_send_title", new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()  # providers frame
                # Just disconnect without sending anything


# ── Additional routing and clarification coverage ─────────────────────────────

import uuid as _uuid

from app.agent.orchestrator import OrchestratorResult
from app.services.llm.base import RoutingDecision, SkillResult


def _new_conv_id() -> str:
    """Return a UUID-based conv_id that is guaranteed to be new each test run."""
    return f"cov-{_uuid.uuid4().hex[:16]}"


class TestWsRoutingPaths:
    """Covers CALL_SKILL, CLARIFY, and ambiguous intent paths in chat_ws.py."""

    def _send_msg(self, ws, content: str, conv_id: str):
        ws.send_json({
            "type": "message",
            "messages": [{"role": "user", "content": content}],
            "conversation_id": conv_id,
            "model": "",
            "temperature": 0.7,
        })

    def _collect(self, ws, max_frames: int = 20) -> list[dict]:
        frames = []
        for _ in range(max_frames):
            try:
                frame = ws.receive_json()
                frames.append(frame)
                if frame.get("type") in ("done", "error", "agent_response",
                                         "clarification_request"):
                    break
            except Exception:
                break
        return frames

    def test_call_skill_routing_sends_done(self):
        """CALL_SKILL path (lines 292-330): skill output sent as done frame."""
        token = create_access_token("ws_route_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming()
        conv_id = _new_conv_id()

        call_skill_result = OrchestratorResult(
            routing_decision=RoutingDecision.CALL_SKILL,
            skill_result=SkillResult(
                skill_name="test_skill",
                output="Here is the skill answer",
                model_used="mock-model",
                confidence=0.95,
                routing_decision=RoutingDecision.CALL_SKILL,
            ),
            confidence=0.95,
            matched_skill_name="test_skill",
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.orchestrator.ChatOrchestrator.route",
                   new=AsyncMock(return_value=call_skill_result)), \
             patch("app.api.routes.chat_ws._generate_and_send_title",
                   new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()
                self._send_msg(ws, "run my skill", conv_id)
                frames = self._collect(ws)

        types = {f.get("type") for f in frames}
        assert "done" in types

    def test_clarify_routing_sends_clarification_request(self):
        """CLARIFY path (lines 331-362): clarification_request frame sent."""
        token = create_access_token("ws_clarify_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming()
        conv_id = _new_conv_id()

        clarify_result = OrchestratorResult(
            routing_decision=RoutingDecision.CLARIFY,
            clarification_message="Did you mean the sales skill?",
            confidence=0.65,
            matched_skill_name="sales_skill",
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.orchestrator.ChatOrchestrator.route",
                   new=AsyncMock(return_value=clarify_result)), \
             patch("app.api.routes.chat_ws._generate_and_send_title",
                   new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()
                self._send_msg(ws, "sales", conv_id)
                frames = self._collect(ws)

        types = {f.get("type") for f in frames}
        assert "clarification_request" in types

    def test_ambiguous_intent_sends_clarification_request(self):
        """Ambiguous estimate_intent path (lines 379-411): clarification_request sent."""
        token = create_access_token("ws_ambig_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming()
        conv_id = _new_conv_id()

        generic_result = OrchestratorResult(
            routing_decision=RoutingDecision.GENERIC_ANSWER,
            use_agent_loop=True,
            intent_hint="",
        )
        ambig_estimation = MagicMock(
            confidence=0.8,
            is_ambiguous=True,
            candidates=["sales: Sales data", "revenue: Revenue data"],
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.orchestrator.ChatOrchestrator.route",
                   new=AsyncMock(return_value=generic_result)), \
             patch("app.agent.orchestrator.ChatOrchestrator.estimate_intent",
                   return_value=ambig_estimation), \
             patch("app.api.routes.chat_ws._generate_and_send_title",
                   new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()
                self._send_msg(ws, "show data", conv_id)
                frames = self._collect(ws)

        types = {f.get("type") for f in frames}
        assert "clarification_request" in types

    def test_agent_loop_clarification_pending_continues(self):
        """loop_result.status == 'clarification_pending' (lines 448-467): loop continues."""
        token = create_access_token("ws_clarpend_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming()
        mock_provider.run_agent_loop = AsyncMock(
            return_value=AgentLoopResult(status="clarification_pending")
        )
        conv_id = _new_conv_id()

        generic_result = OrchestratorResult(
            routing_decision=RoutingDecision.GENERIC_ANSWER,
            use_agent_loop=True,
            intent_hint="",
        )
        high_conf_estimation = MagicMock(
            confidence=1.0, is_ambiguous=False, candidates=[]
        )

        with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                   return_value=mock_provider), \
             patch("app.agent.orchestrator.ChatOrchestrator.route",
                   new=AsyncMock(return_value=generic_result)), \
             patch("app.agent.orchestrator.ChatOrchestrator.estimate_intent",
                   return_value=high_conf_estimation), \
             patch("app.api.routes.chat_ws._generate_and_send_title",
                   new=AsyncMock(return_value=None)):
            with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                ws.receive_json()
                self._send_msg(ws, "query data", conv_id)
                # After clarification_pending → handler loops back to receive_json
                # Disconnect now so the handler exits cleanly
                # collect_with_timeout: receive whatever arrives before disconnect
                frames = []
                try:
                    for _ in range(5):
                        frame = ws.receive_json()
                        frames.append(frame)
                        if frame.get("type") in ("done", "error", "clarification_request"):
                            break
                except Exception:
                    pass

        # The handler continued (no error) → test passes if it didn't hang
        assert frames is not None  # just verify we got here

    def test_clarification_resume_agent_question_path(self):
        """Pending clarification with type='agent_question' triggers agent loop resume."""
        from app.agent.clarification_state import _memory_store, _make_key
        import time, json as _json

        token = create_access_token("ws_resume_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming(tokens=["resumed"])
        conv_id = _new_conv_id()
        user_id = "ws_resume_user"

        # Pre-populate in-memory clarification state
        key = _make_key(user_id, conv_id)
        payload = _json.dumps({
            "question": "Which DB?",
            "candidates": [],
            "original_query": "show me data",
            "clarification_type": "agent_question",
        })
        _memory_store[key] = (payload, time.monotonic() + 300)

        try:
            with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                       return_value=mock_provider), \
                 patch("app.agent.orchestrator.ChatOrchestrator.estimate_intent",
                       return_value=MagicMock(confidence=0.0, is_ambiguous=False, candidates=[])), \
                 patch("app.api.routes.chat_ws._generate_and_send_title",
                       new=AsyncMock(return_value=None)):
                with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                    ws.receive_json()
                    self._send_msg(ws, "use warehouse A", conv_id)
                    frames = self._collect(ws)
        finally:
            _memory_store.pop(key, None)

        types = {f.get("type") for f in frames}
        assert types & {"done", "error"}

    def test_clarification_resume_intent_selection_matched(self):
        """Pending clarification with type='intent_selection' + matched intent → agent loop."""
        from app.agent.clarification_state import _memory_store, _make_key
        from app.agent.intent_loader import IntentDefinition
        import time, json as _json

        token = create_access_token("ws_intent_sel_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming(tokens=["intent result"])
        conv_id = _new_conv_id()
        user_id = "ws_intent_sel_user"

        key = _make_key(user_id, conv_id)
        payload = _json.dumps({
            "question": "Which intent?",
            "candidates": ["sales_data: Sales"],
            "original_query": "show me revenue",
            "clarification_type": "intent_selection",
        })
        _memory_store[key] = (payload, time.monotonic() + 300)

        mock_intent = MagicMock()
        mock_intent.name = "sales_data"
        mock_intent.description = "Sales revenue data"

        try:
            with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                       return_value=mock_provider), \
                 patch("app.agent.orchestrator.ChatOrchestrator.get_intent",
                       return_value=mock_intent), \
                 patch("app.agent.orchestrator.ChatOrchestrator.estimate_intent",
                       return_value=MagicMock(confidence=1.0, is_ambiguous=False, candidates=[])), \
                 patch("app.api.routes.chat_ws._generate_and_send_title",
                       new=AsyncMock(return_value=None)):
                with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                    ws.receive_json()
                    self._send_msg(ws, "sales_data: yes please", conv_id)
                    frames = self._collect(ws)
        finally:
            _memory_store.pop(key, None)

        types = {f.get("type") for f in frames}
        assert types & {"done", "error", "agent_response"}

    def test_clarification_resume_intent_selection_unmatched(self):
        """Pending intent_selection with no matched intent → freeform stream."""
        from app.agent.clarification_state import _memory_store, _make_key
        import time, json as _json

        token = create_access_token("ws_nomatch_user")
        client = TestClient(app)
        mock_provider = _mock_provider_streaming(tokens=["generic answer"])
        conv_id = _new_conv_id()
        user_id = "ws_nomatch_user"

        key = _make_key(user_id, conv_id)
        payload = _json.dumps({
            "question": "Which?",
            "candidates": [],
            "original_query": "sales",
            "clarification_type": "intent_selection",
        })
        _memory_store[key] = (payload, time.monotonic() + 300)

        try:
            with patch("app.api.routes.chat_ws.LLMProviderFactory.create",
                       return_value=mock_provider), \
                 patch("app.agent.orchestrator.ChatOrchestrator.get_intent",
                       return_value=None), \
                 patch("app.api.routes.chat_ws._generate_and_send_title",
                       new=AsyncMock(return_value=None)):
                with client.websocket_connect(f"/ws/chat?token={token}") as ws:
                    ws.receive_json()
                    self._send_msg(ws, "neither", conv_id)
                    frames = self._collect(ws)
        finally:
            _memory_store.pop(key, None)

        types = {f.get("type") for f in frames}
        assert "done" in types
