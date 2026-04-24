"""Tests for SharedToolkit — tool schema generation, dispatch, and intents."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.shared_toolkit import SharedToolkit, _dispatch_combine
from app.agent.tools.query_tools import AgentToolContext


def _make_ctx(store=None, clarification_state=None) -> AgentToolContext:
    return AgentToolContext(
        user_id="u1",
        conversation_id="c1",
        store=store or MagicMock(),
        clarification_state=clarification_state or MagicMock(),
        websocket=None,
    )


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the SharedToolkit singleton between tests."""
    SharedToolkit._instance = None
    yield
    SharedToolkit._instance = None


class TestSingleton:
    def test_same_instance_returned(self):
        t1 = SharedToolkit()
        t2 = SharedToolkit()
        assert t1 is t2

    def test_init_only_runs_once(self):
        t1 = SharedToolkit()
        original_loader = t1.intent_loader
        t2 = SharedToolkit()
        assert t2.intent_loader is original_loader


class TestAnthropicTools:
    def test_returns_list_of_dicts(self):
        toolkit = SharedToolkit()
        tools = toolkit.get_anthropic_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_each_tool_has_required_keys(self):
        toolkit = SharedToolkit()
        for tool in toolkit.get_anthropic_tools():
            assert "name" in tool
            assert "description" in tool
            assert "input_schema" in tool

    def test_contains_query_snowflake(self):
        toolkit = SharedToolkit()
        names = [t["name"] for t in toolkit.get_anthropic_tools()]
        assert "query_snowflake" in names

    def test_contains_all_expected_tools(self):
        toolkit = SharedToolkit()
        names = set(t["name"] for t in toolkit.get_anthropic_tools())
        expected = {
            "query_snowflake", "cortex_analyst", "cortex_complete",
            "cortex_summarize", "query_bigquery", "query_mssql",
            "combine_dataframes", "ask_clarification",
        }
        assert expected == names


class TestOpenAITools:
    def test_returns_list_of_dicts(self):
        toolkit = SharedToolkit()
        tools = toolkit.get_openai_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_each_tool_has_type_function(self):
        toolkit = SharedToolkit()
        for tool in toolkit.get_openai_tools():
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_same_tool_count_as_anthropic(self):
        toolkit = SharedToolkit()
        assert len(toolkit.get_openai_tools()) == len(toolkit.get_anthropic_tools())


class TestAdkFunctions:
    def test_returns_callables(self):
        toolkit = SharedToolkit()
        fns = toolkit.get_adk_functions()
        assert isinstance(fns, list)
        for fn in fns:
            assert callable(fn)

    def test_returns_expected_tools(self):
        toolkit = SharedToolkit()
        names = {fn.__name__ for fn in toolkit.get_adk_functions()}
        assert "query_snowflake" in names
        assert "query_bigquery" in names


class TestStrandsTools:
    def test_returns_callables(self):
        toolkit = SharedToolkit()
        fns = toolkit.get_strands_tools()
        assert isinstance(fns, list)
        for fn in fns:
            assert callable(fn)

    def test_includes_ask_clarification(self):
        toolkit = SharedToolkit()
        names = {fn.__name__ for fn in toolkit.get_strands_tools()}
        assert "ask_clarification" in names


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool_raises(self):
        toolkit = SharedToolkit()
        ctx = _make_ctx()
        with pytest.raises(ValueError, match="Unknown tool"):
            await toolkit.dispatch("nonexistent_tool", {}, ctx)

    @pytest.mark.asyncio
    async def test_dispatch_ask_clarification(self):
        toolkit = SharedToolkit()
        ctx = _make_ctx()
        ctx.clarification_state = MagicMock()
        ctx.clarification_state.set_pending = MagicMock()
        ctx.websocket = AsyncMock()
        ctx.websocket.send_json = AsyncMock()
        result = await toolkit.dispatch(
            "ask_clarification",
            {"message": "Which database?", "candidates": ["snowflake", "bigquery"]},
            ctx,
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_dispatch_combine_dataframes(self):
        toolkit = SharedToolkit()
        import fakeredis
        import pandas as pd
        from app.agent.dataframe_store import DataFrameStore
        store = DataFrameStore(redis_client=fakeredis.FakeRedis(decode_responses=True))
        df_a = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
        df_b = pd.DataFrame({"id": [1, 2], "extra": ["x", "y"]})
        store.store("u1", "c1", "df_a", df_a)
        store.store("u1", "c1", "df_b", df_b)
        ctx = _make_ctx(store=store)

        result = await toolkit.dispatch(
            "combine_dataframes",
            {"label_a": "df_a", "label_b": "df_b", "join_key": "id"},
            ctx,
        )
        assert result["rows"] == 2


class TestIntentsAsSystemContext:
    def test_returns_non_empty_string(self):
        toolkit = SharedToolkit()
        result = toolkit.intents_as_system_context()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_data_assistant_intro(self):
        toolkit = SharedToolkit()
        result = toolkit.intents_as_system_context()
        assert "data assistant" in result.lower()


class TestDispatchCombineHelper:
    @pytest.mark.asyncio
    async def test_dispatch_combine_returns_coroutine(self):
        import fakeredis
        import pandas as pd
        from app.agent.dataframe_store import DataFrameStore
        store = DataFrameStore(redis_client=fakeredis.FakeRedis(decode_responses=True))
        df_a = pd.DataFrame({"id": [1], "v": [1]})
        df_b = pd.DataFrame({"id": [1], "w": [2]})
        store.store("u1", "c1", "a", df_a)
        store.store("u1", "c1", "b", df_b)
        ctx = _make_ctx(store=store)
        result = await _dispatch_combine({"label_a": "a", "label_b": "b", "join_key": "id"}, ctx)
        assert result["rows"] == 1
