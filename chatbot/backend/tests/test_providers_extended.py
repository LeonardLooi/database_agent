"""Extended provider tests — covers init errors, execute_skill, tool loops, Gemini, AWS."""
from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult


def _make_ctx(user_id="u1", conv_id="c1"):
    import fakeredis
    from app.agent.clarification_state import ClarificationState
    from app.agent.dataframe_store import DataFrameStore
    from app.agent.tools.query_tools import AgentToolContext

    redis = fakeredis.FakeRedis(decode_responses=True)
    return AgentToolContext(
        user_id=user_id,
        conversation_id=conv_id,
        store=DataFrameStore(redis_client=redis),
        clarification_state=ClarificationState(redis_client=redis),
        websocket=None,
    )


# ── AnthropicProvider extended ────────────────────────────────────────────────

class TestAnthropicProviderExtended:
    @pytest.fixture(autouse=True)
    def reset_toolkit(self):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None
        yield
        SharedToolkit._instance = None

    @pytest.fixture
    def provider(self):
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        p = AnthropicProvider.__new__(AnthropicProvider)
        p._client = AsyncMock()
        return p

    def test_init_raises_without_api_key(self):
        from app.core.config import settings
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        original = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = ""
        try:
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                AnthropicProvider()
        finally:
            settings.ANTHROPIC_API_KEY = original

    @pytest.mark.asyncio
    async def test_run_agent_loop_tool_call_with_sql_tracking(self, provider):
        tool_block = MagicMock(type="tool_use", name="query_snowflake", id="t1",
                               input={"sql": "SELECT 1", "ctx": {}})
        text_block = MagicMock(type="text", text="Done.")
        resp1 = MagicMock(content=[tool_block], stop_reason="tool_use")
        resp2 = MagicMock(content=[text_block], stop_reason="end_turn")
        provider._client.messages.create = AsyncMock(side_effect=[resp1, resp2])

        ctx = _make_ctx()
        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"sql": "SELECT 1", "rows": 0}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run query")],
                "claude-sonnet-4-20250514",
                ctx,
            )
        assert result.status == "completed"
        assert "SELECT 1" in result.sql_used

    @pytest.mark.asyncio
    async def test_run_agent_loop_tool_error_continues(self, provider):
        tool_block = MagicMock(type="tool_use", name="bad_tool", id="t2", input={})
        text_block = MagicMock(type="text", text="Error handled.")
        resp1 = MagicMock(content=[tool_block], stop_reason="tool_use")
        resp2 = MagicMock(content=[text_block], stop_reason="end_turn")
        provider._client.messages.create = AsyncMock(side_effect=[resp1, resp2])

        ctx = _make_ctx()
        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.side_effect = RuntimeError("bad tool error")
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run bad tool")],
                "claude-sonnet-4-20250514",
                ctx,
            )
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_run_agent_loop_clarification_pending(self, provider):
        tool_block = MagicMock(type="tool_use", name="ask_clarification", id="t3",
                               input={"message": "Which DB?", "candidates": []})
        resp1 = MagicMock(content=[tool_block], stop_reason="tool_use")
        provider._client.messages.create = AsyncMock(return_value=resp1)

        ctx = _make_ctx()
        ctx.clarification_state.set_pending(ctx.user_id, ctx.conversation_id, "Which DB?", [], "query")

        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"status": "pending"}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="query data")],
                "claude-sonnet-4-20250514",
                ctx,
            )
        assert result.status == "clarification_pending"

    @pytest.mark.asyncio
    async def test_execute_skill_success(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"result": "done"}')]
        provider._client.messages.create = AsyncMock(return_value=mock_response)

        skill = SkillSchema(
            name="test_skill",
            description="A test skill",
            instructions="Do X",
        )
        result = await provider.execute_skill("sess1", "run it", skill, {}, "claude-sonnet-4-20250514")
        assert result.skill_name == "test_skill"
        assert result.parsed_output == {"result": "done"}

    @pytest.mark.asyncio
    async def test_execute_skill_error_raises(self, provider):
        from app.agent.skill_registry import SkillSchema
        provider._client.messages.create = AsyncMock(side_effect=RuntimeError("skill failed"))
        skill = SkillSchema(name="s", description="d", instructions="p")
        with pytest.raises(RuntimeError, match="skill failed"):
            await provider.execute_skill("sess1", "run", skill, {}, "claude-sonnet-4-20250514")

    @pytest.mark.asyncio
    async def test_execute_skill_non_json_output(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="plain text output, not JSON")]
        provider._client.messages.create = AsyncMock(return_value=mock_response)
        skill = SkillSchema(name="s", description="d", instructions="p")
        result = await provider.execute_skill("sess1", "run", skill, {}, "claude-sonnet-4-20250514")
        assert result.parsed_output is None
        assert result.output == "plain text output, not JSON"


# ── OpenAIProvider extended ───────────────────────────────────────────────────

class TestOpenAIProviderExtended:
    @pytest.fixture(autouse=True)
    def reset_toolkit(self):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None
        yield
        SharedToolkit._instance = None

    @pytest.fixture
    def provider(self):
        from app.services.llm.providers.openai_provider import OpenAIProvider
        p = OpenAIProvider.__new__(OpenAIProvider)
        p._client = AsyncMock()
        return p

    def test_init_raises_without_api_key(self):
        from app.core.config import settings
        from app.services.llm.providers.openai_provider import OpenAIProvider
        original = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = ""
        try:
            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                OpenAIProvider()
        finally:
            settings.OPENAI_API_KEY = original

    @pytest.mark.asyncio
    async def test_stream_raises_on_error(self, provider):
        provider._client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError("connection error")
        )
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="connection error"):
            async for _ in provider.stream(msgs, "gpt-4o", 0.7):
                pass

    @pytest.mark.asyncio
    async def test_run_agent_loop_with_tool_calls(self, provider):
        tc = MagicMock()
        tc.id = "call1"
        tc.function.name = "query_snowflake"
        tc.function.arguments = json.dumps({"sql": "SELECT 1"})

        msg_with_tools = MagicMock(content="Calling tool...", tool_calls=[tc])
        msg_no_tools = MagicMock(content="Final.", tool_calls=None)
        resp1 = MagicMock(choices=[MagicMock(message=msg_with_tools)])
        resp2 = MagicMock(choices=[MagicMock(message=msg_no_tools)])
        provider._client.chat.completions.create = AsyncMock(side_effect=[resp1, resp2])

        ctx = _make_ctx()
        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"sql": "SELECT 1", "rows": 1}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run query")],
                "gpt-4o",
                ctx,
            )
        assert result.status == "completed"
        assert "SELECT 1" in result.sql_used

    @pytest.mark.asyncio
    async def test_run_agent_loop_tool_error_handled(self, provider):
        tc = MagicMock()
        tc.id = "call2"
        tc.function.name = "bad_tool"
        tc.function.arguments = "{}"

        msg_with_tools = MagicMock(content="", tool_calls=[tc])
        msg_no_tools = MagicMock(content="Recovered.", tool_calls=None)
        resp1 = MagicMock(choices=[MagicMock(message=msg_with_tools)])
        resp2 = MagicMock(choices=[MagicMock(message=msg_no_tools)])
        provider._client.chat.completions.create = AsyncMock(side_effect=[resp1, resp2])

        ctx = _make_ctx()
        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.side_effect = RuntimeError("dispatch failed")
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run bad")],
                "gpt-4o",
                ctx,
            )
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_run_agent_loop_tool_invalid_json_args(self, provider):
        tc = MagicMock()
        tc.id = "call3"
        tc.function.name = "ask_clarification"
        tc.function.arguments = "NOT JSON {{"

        msg_with_tools = MagicMock(content="", tool_calls=[tc])
        msg_no_tools = MagicMock(content="Done.", tool_calls=None)
        resp1 = MagicMock(choices=[MagicMock(message=msg_with_tools)])
        resp2 = MagicMock(choices=[MagicMock(message=msg_no_tools)])
        provider._client.chat.completions.create = AsyncMock(side_effect=[resp1, resp2])

        ctx = _make_ctx()
        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="test")],
                "gpt-4o",
                ctx,
            )
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_run_agent_loop_clarification_pending(self, provider):
        tc = MagicMock()
        tc.id = "call4"
        tc.function.name = "ask_clarification"
        tc.function.arguments = json.dumps({"message": "Which DB?", "candidates": []})

        msg_with_tools = MagicMock(content="", tool_calls=[tc])
        resp1 = MagicMock(choices=[MagicMock(message=msg_with_tools)])
        provider._client.chat.completions.create = AsyncMock(return_value=resp1)

        ctx = _make_ctx()
        ctx.clarification_state.set_pending(ctx.user_id, ctx.conversation_id, "Which DB?", [], "query")

        with patch("app.agent.shared_toolkit.SharedToolkit.dispatch",
                   new_callable=AsyncMock) as mock_dispatch:
            mock_dispatch.return_value = {"status": "pending"}
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="data please")],
                "gpt-4o",
                ctx,
            )
        assert result.status == "clarification_pending"

    @pytest.mark.asyncio
    async def test_execute_skill_success_with_json_output(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        skill = SkillSchema(name="sk", description="d", instructions="p")
        result = await provider.execute_skill("sess", "do it", skill, {}, "gpt-4o")
        assert result.skill_name == "sk"
        assert result.parsed_output == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_skill_non_json_output(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "plain text"
        provider._client.chat.completions.create = AsyncMock(return_value=mock_response)

        skill = SkillSchema(name="sk", description="d", instructions="p")
        result = await provider.execute_skill("sess", "do it", skill, {}, "gpt-4o")
        assert result.parsed_output is None

    @pytest.mark.asyncio
    async def test_execute_skill_error_raises(self, provider):
        from app.agent.skill_registry import SkillSchema
        provider._client.chat.completions.create = AsyncMock(side_effect=RuntimeError("quota"))
        skill = SkillSchema(name="sk", description="d", instructions="p")
        with pytest.raises(RuntimeError, match="quota"):
            await provider.execute_skill("sess", "run", skill, {}, "gpt-4o")


# ── GeminiProvider ────────────────────────────────────────────────────────────

class TestGeminiProvider:
    @pytest.fixture(autouse=True)
    def reset_toolkit(self):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None
        yield
        SharedToolkit._instance = None

    @pytest.fixture
    def provider(self):
        from app.services.llm.providers.gemini_provider import GeminiProvider
        p = GeminiProvider.__new__(GeminiProvider)
        p._credentials = MagicMock()
        p._client = MagicMock()
        return p

    def test_is_available_returns_true(self):
        from app.services.llm.providers.gemini_provider import GeminiProvider
        assert GeminiProvider.is_available() is True

    def test_to_gemini_contents_maps_assistant_role(self, provider):
        msgs = [
            MsgIn(role="user", content="hello"),
            MsgIn(role="assistant", content="hi there"),
        ]
        contents = provider._to_gemini_contents(msgs)
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"
        assert contents[1]["parts"][0]["text"] == "hi there"

    def test_resolve_credentials_ambient_adc(self, provider):
        from app.core.config import settings
        orig_sa = settings.GCP_IMPERSONATE_SA
        orig_creds = settings.GOOGLE_APPLICATION_CREDENTIALS
        settings.GCP_IMPERSONATE_SA = ""
        settings.GOOGLE_APPLICATION_CREDENTIALS = ""
        mock_creds = MagicMock()
        try:
            with patch("google.auth.default", return_value=(mock_creds, "proj")):
                result = provider._resolve_credentials()
            assert result is mock_creds
        finally:
            settings.GCP_IMPERSONATE_SA = orig_sa
            settings.GOOGLE_APPLICATION_CREDENTIALS = orig_creds

    def test_resolve_credentials_ambient_adc_failure_raises_auth_config_error(self, provider):
        from app.core.config import settings
        from app.core.exceptions import AuthConfigError
        orig_sa = settings.GCP_IMPERSONATE_SA
        orig_creds = settings.GOOGLE_APPLICATION_CREDENTIALS
        settings.GCP_IMPERSONATE_SA = ""
        settings.GOOGLE_APPLICATION_CREDENTIALS = ""
        try:
            import google.auth.exceptions
            with patch("google.auth.default",
                       side_effect=google.auth.exceptions.DefaultCredentialsError("no creds")):
                with pytest.raises(AuthConfigError):
                    provider._resolve_credentials()
        finally:
            settings.GCP_IMPERSONATE_SA = orig_sa
            settings.GOOGLE_APPLICATION_CREDENTIALS = orig_creds

    def test_resolve_credentials_impersonation_path(self, provider):
        from app.core.config import settings
        orig_sa = settings.GCP_IMPERSONATE_SA
        settings.GCP_IMPERSONATE_SA = "sa@proj.iam.gserviceaccount.com"
        mock_creds = MagicMock()
        mock_impersonated = MagicMock()
        try:
            with patch("google.auth.default", return_value=(mock_creds, "proj")), \
                 patch("google.auth.impersonated_credentials.Credentials",
                       return_value=mock_impersonated):
                result = provider._resolve_credentials()
            assert result is mock_impersonated
        finally:
            settings.GCP_IMPERSONATE_SA = orig_sa

    def test_resolve_credentials_key_file_path(self, provider):
        from app.core.config import settings
        orig_sa = settings.GCP_IMPERSONATE_SA
        orig_creds_file = settings.GOOGLE_APPLICATION_CREDENTIALS
        settings.GCP_IMPERSONATE_SA = ""
        settings.GOOGLE_APPLICATION_CREDENTIALS = "/path/to/key.json"
        mock_creds = MagicMock()
        try:
            with patch("google.oauth2.service_account.Credentials.from_service_account_file",
                       return_value=mock_creds):
                result = provider._resolve_credentials()
            assert result is mock_creds
        finally:
            settings.GCP_IMPERSONATE_SA = orig_sa
            settings.GOOGLE_APPLICATION_CREDENTIALS = orig_creds_file

    def test_resolve_credentials_import_error_raises(self, provider):
        from app.core.exceptions import AuthConfigError
        # Temporarily remove google.auth from sys.modules to force ImportError
        import sys
        google_auth = sys.modules.pop("google.auth", None)
        google_auth_exceptions = sys.modules.pop("google.auth.exceptions", None)
        google_auth_impersonated = sys.modules.pop("google.auth.impersonated_credentials", None)
        google_auth_transport = sys.modules.pop("google.auth.transport.requests", None)
        google_oauth2 = sys.modules.pop("google.oauth2.service_account", None)
        try:
            with patch.dict("sys.modules", {"google.auth": None}):
                with pytest.raises(AuthConfigError, match="google-auth is not installed"):
                    provider._resolve_credentials()
        finally:
            if google_auth:
                sys.modules["google.auth"] = google_auth
            if google_auth_exceptions:
                sys.modules["google.auth.exceptions"] = google_auth_exceptions
            if google_auth_impersonated:
                sys.modules["google.auth.impersonated_credentials"] = google_auth_impersonated
            if google_auth_transport:
                sys.modules["google.auth.transport.requests"] = google_auth_transport
            if google_oauth2:
                sys.modules["google.oauth2.service_account"] = google_oauth2

    def test_init_with_mocked_credentials(self):
        from google import genai
        from app.services.llm.providers.gemini_provider import GeminiProvider
        mock_creds = MagicMock()
        mock_client = MagicMock()
        with patch.object(GeminiProvider, "_resolve_credentials", return_value=mock_creds), \
             patch("google.genai.Client", return_value=mock_client):
            p = GeminiProvider()
        assert p._credentials is mock_creds
        assert p._client is mock_client

    @pytest.mark.asyncio
    async def test_stream_yields_text(self, provider):
        async def _gen():
            for text in ["Hello", " world"]:
                chunk = MagicMock()
                chunk.text = text
                yield chunk

        async def _mock_stream(*args, **kwargs):
            return _gen()

        provider._client.aio.models.generate_content_stream = _mock_stream
        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "gemini-2.5-flash", 0.7):
            tokens.append(tok)
        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_skips_empty_text_chunks(self, provider):
        async def _gen():
            for text in ["", "hello", ""]:
                chunk = MagicMock()
                chunk.text = text
                yield chunk

        async def _mock_stream(*args, **kwargs):
            return _gen()

        provider._client.aio.models.generate_content_stream = _mock_stream
        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "gemini-2.5-flash", 0.7):
            tokens.append(tok)
        assert tokens == ["hello"]

    @pytest.mark.asyncio
    async def test_stream_raises_on_error(self, provider):
        async def _mock_stream(*args, **kwargs):
            raise RuntimeError("quota exceeded")

        provider._client.aio.models.generate_content_stream = _mock_stream
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="quota exceeded"):
            async for _ in provider.stream(msgs, "gemini-2.5-flash", 0.7):
                pass

    @pytest.mark.asyncio
    async def test_generate_returns_text(self, provider):
        mock_response = MagicMock(text="Generated response")
        provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        msgs = [MsgIn(role="user", content="hi")]
        result = await provider.generate(msgs, "gemini-2.5-flash")
        assert result == "Generated response"

    @pytest.mark.asyncio
    async def test_generate_raises_on_error(self, provider):
        provider._client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="API error"):
            await provider.generate(msgs, "gemini-2.5-flash")

    @pytest.mark.asyncio
    async def test_run_agent_loop_credential_refresh_failure(self, provider):
        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.run_in_executor = AsyncMock(
                side_effect=RuntimeError("token expired")
            )
            ctx = _make_ctx()
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="hi")],
                "gemini-2.5-flash",
                ctx,
            )
        assert result.status == "error"
        assert "credential refresh" in result.error.lower()

    @pytest.mark.asyncio
    async def test_run_agent_loop_completed(self, provider):
        from google.adk.agents import LlmAgent
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.tools import FunctionTool
        import google.genai.types as genai_types

        mock_creds = MagicMock()
        provider._credentials = mock_creds

        # Mock credential refresh
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = MagicMock()
        mock_event.content.parts = [MagicMock(text="Final answer")]

        async def _run_async(*args, **kwargs):
            yield mock_event

        mock_runner = MagicMock()
        mock_runner.run_async = _run_async

        mock_session = MagicMock()
        mock_session.id = "sess-1"
        mock_session_service = MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        ctx = _make_ctx()

        with patch("asyncio.get_event_loop") as mock_loop, \
             patch("google.adk.agents.LlmAgent", return_value=MagicMock()), \
             patch("google.adk.runners.Runner", return_value=mock_runner), \
             patch("google.adk.sessions.InMemorySessionService",
                   return_value=mock_session_service), \
             patch("google.adk.tools.FunctionTool", side_effect=lambda fn: MagicMock()):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="hello ADK")],
                "gemini-2.5-flash",
                ctx,
            )
        assert result.status == "completed"
        assert result.explanation == "Final answer"

    @pytest.mark.asyncio
    async def test_run_agent_loop_error(self, provider):
        async def _fail_run_async(*args, **kwargs):
            raise RuntimeError("runner failed")
            yield  # pragma: no cover

        mock_runner = MagicMock()
        mock_runner.run_async = _fail_run_async
        mock_session = MagicMock()
        mock_session.id = "sess-err"
        mock_session_service = MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        ctx = _make_ctx()
        with patch("asyncio.get_event_loop") as mock_loop, \
             patch("google.adk.agents.LlmAgent", return_value=MagicMock()), \
             patch("google.adk.runners.Runner", return_value=mock_runner), \
             patch("google.adk.sessions.InMemorySessionService",
                   return_value=mock_session_service), \
             patch("google.adk.tools.FunctionTool", side_effect=lambda fn: MagicMock()):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="hi")],
                "gemini-2.5-flash",
                ctx,
            )
        assert result.status == "error"

    @pytest.mark.asyncio
    async def test_run_agent_loop_clarification_pending(self, provider):
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content = MagicMock()
        mock_event.content.parts = [MagicMock(text="need clarification")]

        async def _run_async(*args, **kwargs):
            yield mock_event

        mock_runner = MagicMock()
        mock_runner.run_async = _run_async
        mock_session = MagicMock()
        mock_session.id = "sess-2"
        mock_session_service = MagicMock()
        mock_session_service.create_session = AsyncMock(return_value=mock_session)

        ctx = _make_ctx()
        ctx.clarification_state.set_pending(ctx.user_id, ctx.conversation_id, "Which DB?", [], "query")

        with patch("asyncio.get_event_loop") as mock_loop, \
             patch("google.adk.agents.LlmAgent", return_value=MagicMock()), \
             patch("google.adk.runners.Runner", return_value=mock_runner), \
             patch("google.adk.sessions.InMemorySessionService",
                   return_value=mock_session_service), \
             patch("google.adk.tools.FunctionTool", side_effect=lambda fn: MagicMock()):
            mock_loop.return_value.run_in_executor = AsyncMock(return_value=None)
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="data?")],
                "gemini-2.5-flash",
                ctx,
            )
        assert result.status == "clarification_pending"

    @pytest.mark.asyncio
    async def test_execute_skill_success(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock(text='{"output": "good"}')
        provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        skill = SkillSchema(name="sk", description="d", instructions="p")
        result = await provider.execute_skill("sess", "run it", skill, {}, "gemini-2.5-flash")
        assert result.skill_name == "sk"
        assert result.parsed_output == {"output": "good"}

    @pytest.mark.asyncio
    async def test_execute_skill_non_json_output(self, provider):
        from app.agent.skill_registry import SkillSchema
        mock_response = MagicMock(text="not json at all")
        provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        skill = SkillSchema(name="sk", description="d", instructions="p")
        result = await provider.execute_skill("sess", "run it", skill, {}, "gemini-2.5-flash")
        assert result.parsed_output is None

    @pytest.mark.asyncio
    async def test_execute_skill_error_raises(self, provider):
        from app.agent.skill_registry import SkillSchema
        provider._client.aio.models.generate_content = AsyncMock(
            side_effect=RuntimeError("Gemini error")
        )
        skill = SkillSchema(name="sk", description="d", instructions="p")
        with pytest.raises(RuntimeError, match="Gemini error"):
            await provider.execute_skill("sess", "run it", skill, {}, "gemini-2.5-flash")


# ── AWSBedrockProvider ────────────────────────────────────────────────────────

class TestAWSBedrockProvider:
    @pytest.fixture(autouse=True)
    def reset_toolkit(self):
        from app.agent.shared_toolkit import SharedToolkit
        SharedToolkit._instance = None
        yield
        SharedToolkit._instance = None

    @pytest.fixture
    def provider(self):
        from app.services.llm.providers.aws_provider import AWSBedrockProvider
        p = AWSBedrockProvider.__new__(AWSBedrockProvider)
        p._bedrock = MagicMock()
        return p

    def test_provider_name(self, provider):
        assert provider.provider_name == "aws"

    def test_is_available_returns_bool(self):
        from app.services.llm.providers.aws_provider import AWSBedrockProvider
        result = AWSBedrockProvider.is_available()
        assert isinstance(result, bool)

    def test_format_messages(self, provider):
        msgs = [MsgIn(role="user", content="hello")]
        formatted = provider._format_messages(msgs)
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"][0]["text"] == "hello"

    @pytest.mark.asyncio
    async def test_stream_yields_text(self, provider):
        async def _mock_stream(messages):
            for text in ["Hello", " world"]:
                yield {"contentBlockDelta": {"delta": {"text": text}}}

        provider._bedrock.stream = _mock_stream
        provider._bedrock.update_config = MagicMock()
        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "amazon.nova-lite-v1:0", 0.7):
            tokens.append(tok)
        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_stream_skips_non_content_events(self, provider):
        async def _mock_stream(messages):
            yield {"messageStart": {"role": "assistant"}}
            yield {"contentBlockDelta": {"delta": {"text": "data"}}}
            yield {"messageStop": {}}

        provider._bedrock.stream = _mock_stream
        provider._bedrock.update_config = MagicMock()
        msgs = [MsgIn(role="user", content="hi")]
        tokens = []
        async for tok in provider.stream(msgs, "amazon.nova-lite-v1:0", 0.7):
            tokens.append(tok)
        assert tokens == ["data"]

    @pytest.mark.asyncio
    async def test_stream_raises_on_error(self, provider):
        async def _fail(messages):
            raise RuntimeError("bedrock error")
            yield  # pragma: no cover

        provider._bedrock.stream = _fail
        provider._bedrock.update_config = MagicMock()
        msgs = [MsgIn(role="user", content="hi")]
        with pytest.raises(RuntimeError, match="bedrock error"):
            async for _ in provider.stream(msgs, "amazon.nova-lite-v1:0", 0.7):
                pass

    @pytest.mark.asyncio
    async def test_generate_concatenates_stream(self, provider):
        async def _mock_stream(messages):
            for text in ["He", "ll", "o"]:
                yield {"contentBlockDelta": {"delta": {"text": text}}}

        provider._bedrock.stream = _mock_stream
        provider._bedrock.update_config = MagicMock()
        msgs = [MsgIn(role="user", content="hi")]
        result = await provider.generate(msgs, "amazon.nova-lite-v1:0")
        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_run_agent_loop_completed(self, provider):
        from strands import Agent
        from strands.models.bedrock import BedrockModel

        mock_agent = MagicMock()
        mock_agent.__call__ = MagicMock(return_value="Agent answer")

        ctx = _make_ctx()

        with patch("boto3.Session") as mock_session_cls, \
             patch("strands.models.bedrock.BedrockModel", return_value=MagicMock()), \
             patch("strands.Agent", return_value=mock_agent), \
             patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = "Agent answer"
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run agent")],
                "amazon.nova-pro-v1:0",
                ctx,
            )
        assert result.status == "completed"
        assert result.explanation == "Agent answer"

    @pytest.mark.asyncio
    async def test_run_agent_loop_error(self, provider):
        ctx = _make_ctx()

        with patch("boto3.Session"), \
             patch("strands.models.bedrock.BedrockModel", return_value=MagicMock()), \
             patch("strands.Agent", return_value=MagicMock()), \
             patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = RuntimeError("strands failed")
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="run agent")],
                "amazon.nova-pro-v1:0",
                ctx,
            )
        assert result.status == "error"
        assert "strands failed" in result.error

    @pytest.mark.asyncio
    async def test_run_agent_loop_clarification_pending(self, provider):
        ctx = _make_ctx()
        ctx.clarification_state.set_pending(ctx.user_id, ctx.conversation_id, "Which table?", [], "query")

        with patch("boto3.Session"), \
             patch("strands.models.bedrock.BedrockModel", return_value=MagicMock()), \
             patch("strands.Agent", return_value=MagicMock()), \
             patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = "need more info"
            result = await provider.run_agent_loop(
                [MsgIn(role="user", content="data?")],
                "amazon.nova-pro-v1:0",
                ctx,
            )
        assert result.status == "clarification_pending"


# ── Provider __init__ successful paths ────────────────────────────────────────

class TestProviderInitPaths:
    def test_anthropic_init_with_valid_key(self):
        from app.core.config import settings
        from app.services.llm.providers.anthropic_provider import AnthropicProvider
        original = settings.ANTHROPIC_API_KEY
        settings.ANTHROPIC_API_KEY = "test-key-valid"
        try:
            with patch("anthropic.AsyncAnthropic", return_value=MagicMock()) as mock_cls:
                p = AnthropicProvider()
            mock_cls.assert_called_once_with(api_key="test-key-valid")
            assert p._client is not None
        finally:
            settings.ANTHROPIC_API_KEY = original

    def test_openai_init_with_valid_key(self):
        from app.core.config import settings
        from app.services.llm.providers.openai_provider import OpenAIProvider
        original = settings.OPENAI_API_KEY
        settings.OPENAI_API_KEY = "test-openai-valid"
        try:
            with patch("openai.AsyncOpenAI", return_value=MagicMock()) as mock_cls:
                p = OpenAIProvider()
            mock_cls.assert_called_once_with(api_key="test-openai-valid")
            assert p._client is not None
        finally:
            settings.OPENAI_API_KEY = original

    def test_aws_init_with_mocked_strands(self):
        from app.services.llm.providers.aws_provider import AWSBedrockProvider
        mock_bedrock = MagicMock()
        with patch("boto3.Session") as mock_session_cls, \
             patch("strands.models.bedrock.BedrockModel", return_value=mock_bedrock):
            mock_session_cls.return_value = MagicMock()
            p = AWSBedrockProvider()
        assert p._bedrock is mock_bedrock

    def test_aws_is_available_import_error_returns_false(self):
        with patch.dict("sys.modules", {"strands": None, "strands.models.bedrock": None,
                                         "strands.models": None}):
            from app.services.llm.providers.aws_provider import AWSBedrockProvider
            result = AWSBedrockProvider.is_available()
            assert result is False

    @pytest.mark.asyncio
    async def test_aws_run_agent_loop_strands_not_installed_raises(self):
        from app.services.llm.providers.aws_provider import AWSBedrockProvider
        p = AWSBedrockProvider.__new__(AWSBedrockProvider)
        p._bedrock = MagicMock()
        ctx = _make_ctx()
        with patch.dict("sys.modules", {"strands": None, "strands.models": None,
                                         "strands.models.bedrock": None}):
            with pytest.raises((RuntimeError, ImportError)):
                await p.run_agent_loop(
                    [MsgIn(role="user", content="hi")],
                    "amazon.nova-lite-v1:0",
                    ctx,
                )
