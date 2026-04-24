"""Tests for Anthropic and OpenAI providers using mocked clients."""
from __future__ import annotations

import json
import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_ctx(user_id="u1", conv_id="c1"):
    from app.agent.clarification_state import ClarificationState
    from app.agent.dataframe_store import DataFrameStore
    from app.agent.tools.query_tools import AgentToolContext
    import fakeredis
    redis = fakeredis.FakeRedis(decode_responses=True)
    return AgentToolContext(
        user_id=user_id,
        conversation_id=conv_id,
        store=DataFrameStore(redis_client=redis),
        clarification_state=ClarificationState(redis_client=redis),
        websocket=None,
    )


# ── AnthropicProvider ─────────────────────────────────────────────────────────

class TestAnthropicProvider:
    @pytest.fixture
    def provider(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("anthropic.AsyncAnthropic"):
                from app.core.config import settings
                original = settings.ANTHROPIC_API_KEY
                settings.ANTHROPIC_API_KEY = "test-key"
                from app.services.llm.providers.anthropic_provider import AnthropicProvider
                p = AnthropicProvider.__new__(AnthropicProvider)
                p._client = AsyncMock()
                yield p
                settings.ANTHROPIC_API_KEY = original

    def test_provider_name(self, provider):
        assert provider.provider_name == "anthropic"

    def test_available_models_non_empty(self, provider):
        assert len(provider.available_models) > 0

    def test_is_available_with_key(self):
        from app.core.config import settings
        original = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = "some-key"
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        assert AnthropicProvider.is_available() is True
        settings.ANTHROPIC_API_KEY = original

    def test_is_available_without_key(self):
        from app.core.config import settings
        original = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = ""
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        assert AnthropicProvider.is_available() is False
        settings.ANTHROPIC_API_KEY = original

    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self, provider):
        from contextlib import asynccontextmanager

        async def _text_stream():
            for t in ["Hello", " ", "world"]:
                yield t

        @asynccontextmanager
        async def _mock_stream_ctx(*args, **kwargs):
            ctx = MagicMock()
            ctx.text_stream = _text_stream()
            yield ctx

        provider._client.messages.stream = _mock_stream_ctx

        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "claude-sonnet-4-20250514", 0.7):
            tokens.append(tok)
        assert tokens == ["Hello", " ", "world"]

    @pytest.mark.asyncio
    async def test_stream_raises_on_error(self, provider):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def _error_ctx(*args, **kwargs):
            raise RuntimeError("API error")
            yield  # pragma: no cover

        provider._client.messages.stream = _error_ctx

        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="API error"):
            async for _ in provider.stream(msgs, "claude-sonnet-4-20250514", 0.7):
                pass

    @pytest.mark.asyncio
    async def test_generate_returns_text(self, provider):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated text")]
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        msgs = [MsgIn(role="user", content="title me")]
        result = await provider.generate(msgs, "claude-sonnet-4-20250514")
        assert result == "Generated text"

    @pytest.mark.asyncio
    async def test_generate_raises_on_error(self, provider):
        provider._client.messages.create = AsyncMock(side_effect=RuntimeError("quota"))
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="quota"):
            await provider.generate(msgs, "claude-sonnet-4-20250514")

    @pytest.mark.asyncio
    async def test_run_agent_loop_no_tool_calls_completes(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Here is the answer."
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.stop_reason = "end_turn"
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        ctx = _make_ctx()
        result = await provider.run_agent_loop(
            [MsgIn(role="user", content="What is 2+2?")],
            "claude-sonnet-4-20250514",
            ctx,
        )
        assert result.status == "completed"
        assert result.explanation == "Here is the answer."
        SharedToolkit._instance = None

    @pytest.mark.asyncio
    async def test_run_agent_loop_api_error_returns_error_status(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        provider._client.messages.create = AsyncMock(side_effect=RuntimeError("connection error"))
        ctx = _make_ctx()
        result = await provider.run_agent_loop(
            [MsgIn(role="user", content="hi")],
            "claude-sonnet-4-20250514",
            ctx,
        )
        assert result.status == "error"
        assert "connection error" in result.error
        SharedToolkit._instance = None

    @pytest.mark.asyncio
    async def test_run_agent_loop_tool_call_dispatch(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        # First call: tool_use; Second call: end_turn
        tool_block = MagicMock()
        tool_block.type = "tool_use"
        tool_block.name = "ask_clarification"
        tool_block.id = "tu1"
        tool_block.input = {"message": "Which DB?", "candidates": []}

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = "I called the tool."

        resp1 = MagicMock()
        resp1.content = [tool_block]
        resp1.stop_reason = "tool_use"

        resp2 = MagicMock()
        resp2.content = [text_block]
        resp2.stop_reason = "end_turn"

        provider._client.messages.create = AsyncMock(side_effect=[resp1, resp2])
        ctx = _make_ctx()
        ctx.websocket = AsyncMock()

        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch", new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"status": "pending"}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="show me data")],
                "claude-sonnet-4-20250514",
                ctx,
            )
        assert result.status in ("completed", "clarification_pending")
        SharedToolkit._instance = None


# ── OpenAIProvider ────────────────────────────────────────────────────────────

class TestOpenAIProvider:
    @pytest.fixture
    def provider(self):
        from app.core.config import settings
        original = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = "test-openai-key"
        from app.services.llm.providers.openai_provider import OpenAIProvider
        p = OpenAIProvider.__new__(OpenAIProvider)
        p._client = AsyncMock()
        yield p
        settings.OPENAI_API_KEY = original

    def test_provider_name(self, provider):
        assert provider.provider_name == "openai"

    def test_is_available_with_key(self):
        from app.core.config import settings
        original = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = "some-key"
        from app.services.llm.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider.is_available() is True
        settings.OPENAI_API_KEY = original

    def test_is_available_without_key(self):
        from app.core.config import settings
        original = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = ""
        from app.services.llm.providers.openai_provider import OpenAIProvider
        assert OpenAIProvider.is_available() is False
        settings.OPENAI_API_KEY = original

    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self, provider):
        async def _chunks():
            for text in ["Hello", " world"]:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta = MagicMock(content=text)
                yield chunk

        provider._client.chat.completions.create = AsyncMock(return_value=_chunks())

        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "gpt-4o", 0.7):
            tokens.append(tok)
        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_o1_skips_temperature(self, provider):
        call_kwargs = {}

        async def _mock_create(**kwargs):
            call_kwargs.update(kwargs)
            async def _empty():
                return
                yield  # make it async generator
            return _empty()

        provider._client.chat.completions.create = _mock_create

        msgs = [MsgIn(role="user", content="hi")]
        async for _ in provider.stream(msgs, "o1", 0.7):
            pass
        assert "temperature" not in call_kwargs

    @pytest.mark.asyncio
    async def test_generate_returns_content(self, provider):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        msgs = [MsgIn(role="user", content="hi")]
        result = await provider.generate(msgs, "gpt-4o")
        assert result == "Generated response"

    @pytest.mark.asyncio
    async def test_generate_raises_on_error(self, provider):
        provider._client.chat.completions.create = AsyncMock(side_effect=RuntimeError("quota"))
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError):
            await provider.generate(msgs, "gpt-4o")

    @pytest.mark.asyncio
    async def test_run_agent_loop_no_tool_calls_completes(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        mock_msg = MagicMock()
        mock_msg.content = "Final answer."
        mock_msg.tool_calls = None
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_msg
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        ctx = _make_ctx()
        result = await provider.run_agent_loop(
            [MsgIn(role="user", content="What is 2+2?")],
            "gpt-4o",
            ctx,
        )
        assert result.status == "completed"
        assert result.explanation == "Final answer."
        SharedToolkit._instance = None

    @pytest.mark.asyncio
    async def test_run_agent_loop_error_returns_error_status(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        provider._client.chat.completions.create = AsyncMock(side_effect=RuntimeError("API down"))
        ctx = _make_ctx()
        result = await provider.run_agent_loop(
            [MsgIn(role="user", content="hi")],
            "gpt-4o",
            ctx,
        )
        assert result.status == "error"
        assert "API down" in result.error
        SharedToolkit._instance = None

    @pytest.mark.asyncio
    async def test_run_agent_loop_o1_uses_developer_role(self, provider):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None

        call_kwargs = {}
        mock_msg = MagicMock()
        mock_msg.content = "answer"
        mock_msg.tool_calls = None
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = mock_msg

        async def _capture(**kwargs):
            call_kwargs.update(kwargs)
            return mock_response

        provider._client.chat.completions.create = _capture
        ctx = _make_ctx()
        await provider.run_agent_loop(
            [MsgIn(role="user", content="test")],
            "o1",
            ctx,
        )
        messages = call_kwargs.get("messages", [])
        system_msg = next((m for m in messages if m.get("role") in ("system", "developer")), None)
        assert system_msg is not None
        assert system_msg["role"] == "developer"
        SharedToolkit._instance = None
