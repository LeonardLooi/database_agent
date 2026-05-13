"""Tests for query_tools — all tool functions with mocked connectors."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import fakeredis
import pandas as pd
import pytest

from app.agent.clarification_state import ClarificationState
from app.agent.dataframe_store import DataFrameStore
from app.agent.tools.query_tools import (
    AgentToolContext,
    _make_summary,
    call_rest_api,
    cortex_analyst,
    cortex_complete,
    cortex_summarize,
    query_bigquery,
    query_mssql,
    query_snowflake,
)


@pytest.fixture
def redis_client():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def store(redis_client):
    return DataFrameStore(redis_client=redis_client)


@pytest.fixture
def clarification_state(redis_client):
    return ClarificationState(redis_client=redis_client)


@pytest.fixture
def ctx(store, clarification_state):
    return AgentToolContext(
        user_id="u1",
        conversation_id="c1",
        store=store,
        clarification_state=clarification_state,
        websocket=None,
    )


def _mock_connector_cls(result_df=None, side_effect=None):
    mock = MagicMock()
    if side_effect:
        mock.execute_query.side_effect = side_effect
    else:
        mock.execute_query.return_value = result_df if result_df is not None else pd.DataFrame({"col": [1, 2]})
    return mock


class TestMakeSummary:
    def test_returns_required_keys(self):
        df = pd.DataFrame({"id": [1, 2], "name": ["A", "B"]})
        summary = _make_summary(df, "test_label", False)
        assert summary["label"] == "test_label"
        assert summary["rows"] == 2
        assert summary["columns"] == ["id", "name"]
        assert len(summary["sample"]) == 2
        assert summary["truncated"] is False

    def test_truncated_notice_when_true(self):
        df = pd.DataFrame({"x": range(10)})
        summary = _make_summary(df, "lbl", True)
        assert summary["truncated"] is True
        assert summary["truncated_notice"] != ""

    def test_sample_capped_at_3(self):
        df = pd.DataFrame({"x": range(10)})
        summary = _make_summary(df, "lbl", False)
        assert len(summary["sample"]) == 3


class TestQuerySnowflake:
    @pytest.mark.asyncio
    async def test_query_snowflake_success(self, ctx):
        df = pd.DataFrame({"id": [1, 2], "v": ["a", "b"]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await query_snowflake(sql="SELECT id, v FROM t", ctx=ctx)

        assert result["rows"] == 2
        assert "id" in result["columns"]
        assert result["label"] == "snowflake_result"
        # DataFrame should be stored
        stored = ctx.store.retrieve("u1", "c1", "snowflake_result")
        assert stored is not None

    @pytest.mark.asyncio
    async def test_query_snowflake_custom_label(self, ctx):
        df = pd.DataFrame({"x": [1]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await query_snowflake(sql="SELECT 1", ctx=ctx, label="my_result")

        assert result["label"] == "my_result"


class TestCortexAnalyst:
    @pytest.mark.asyncio
    async def test_cortex_analyst_success(self, ctx):
        df = pd.DataFrame({"revenue": [100, 200]})
        mock_connector = MagicMock()
        mock_connector.cortex_analyst.return_value = {
            "df": df,
            "sql": "SELECT revenue FROM table",
            "explanation": "Revenue data",
            "error": None,
        }

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await cortex_analyst(question="What is revenue?", ctx=ctx)

        assert result["rows"] == 2
        assert result["sql"] == "SELECT revenue FROM table"

    @pytest.mark.asyncio
    async def test_cortex_analyst_error_returned(self, ctx):
        mock_connector = MagicMock()
        mock_connector.cortex_analyst.return_value = {
            "df": pd.DataFrame(),
            "sql": "",
            "explanation": "",
            "error": "Permission denied",
        }

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await cortex_analyst(question="What is revenue?", ctx=ctx)

        assert "error" in result
        assert result["error"] == "Permission denied"
        assert result["rows"] == 0


class TestCortexComplete:
    @pytest.mark.asyncio
    async def test_cortex_complete_success(self, ctx):
        mock_connector = MagicMock()
        mock_connector.cortex_complete.return_value = "Generated text here."

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await cortex_complete(prompt="Summarize this.", ctx=ctx)

        assert result["result"] == "Generated text here."
        assert result["model"] == "mistral-large2"


class TestCortexSummarize:
    @pytest.mark.asyncio
    async def test_cortex_summarize_success(self, ctx):
        mock_connector = MagicMock()
        mock_connector.cortex_summarize.return_value = "Short summary."

        with patch("app.agent.tools.query_tools.SnowflakeConnector", return_value=mock_connector):
            result = await cortex_summarize(text="Long text here.", ctx=ctx)

        assert result["summary"] == "Short summary."


class TestQueryBigQuery:
    @pytest.mark.asyncio
    async def test_query_bigquery_success(self, ctx):
        df = pd.DataFrame({"project": ["A", "B"], "cost": [100, 200]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.BigQueryConnector", return_value=mock_connector):
            result = await query_bigquery(sql="SELECT project, cost FROM t", ctx=ctx)

        assert result["rows"] == 2
        assert "project" in result["columns"]
        assert result["label"] == "bigquery_result"

    @pytest.mark.asyncio
    async def test_query_bigquery_custom_label(self, ctx):
        df = pd.DataFrame({"x": [1]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.BigQueryConnector", return_value=mock_connector):
            result = await query_bigquery(sql="SELECT 1", ctx=ctx, label="bq_custom")

        assert result["label"] == "bq_custom"


class TestQueryMssql:
    @pytest.mark.asyncio
    async def test_query_mssql_success(self, ctx):
        df = pd.DataFrame({"order_id": [1, 2], "amount": [100.0, 200.0]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.MSSQLConnector", return_value=mock_connector):
            result = await query_mssql(sql="SELECT order_id, amount FROM orders", ctx=ctx)

        assert result["rows"] == 2
        assert "order_id" in result["columns"]
        assert result["label"] == "mssql_result"

    @pytest.mark.asyncio
    async def test_query_mssql_custom_label(self, ctx):
        df = pd.DataFrame({"x": [1]})
        mock_connector = _mock_connector_cls(result_df=df)

        with patch("app.agent.tools.query_tools.MSSQLConnector", return_value=mock_connector):
            result = await query_mssql(sql="SELECT 1", ctx=ctx, label="mssql_custom")

        assert result["label"] == "mssql_custom"


class TestCallRestApi:
    @pytest.mark.asyncio
    async def test_call_rest_api_success_json(self, ctx):
        from unittest.mock import AsyncMock

        mock_connector = AsyncMock()
        mock_connector.call.return_value = {"data": {"answer": "Revenue is $1M"}, "status": 200}

        with patch(
            "app.agent.tools.query_tools.RestConnector",
            return_value=mock_connector,
        ):
            result = await call_rest_api(
                prompt="What is the revenue?",
                ctx=ctx,
                url="https://api.example.com/insights",
                method="POST",
            )

        assert result["label"] == "rest_result"
        assert result["status"] == 200
        assert result["data"] == {"answer": "Revenue is $1M"}
        mock_connector.call.assert_called_once_with("What is the revenue?")

    @pytest.mark.asyncio
    async def test_call_rest_api_custom_label(self, ctx):
        from unittest.mock import AsyncMock

        mock_connector = AsyncMock()
        mock_connector.call.return_value = {"data": "ok", "status": 200}

        with patch(
            "app.agent.tools.query_tools.RestConnector",
            return_value=mock_connector,
        ):
            result = await call_rest_api(
                prompt="test",
                ctx=ctx,
                url="https://api.example.com/v2",
                label="custom_rest",
            )

        assert result["label"] == "custom_rest"

    @pytest.mark.asyncio
    async def test_call_rest_api_propagates_error(self, ctx):
        import httpx
        from unittest.mock import AsyncMock

        mock_connector = AsyncMock()
        mock_connector.call.side_effect = httpx.HTTPStatusError(
            "503", request=MagicMock(), response=MagicMock()
        )

        with patch(
            "app.agent.tools.query_tools.RestConnector",
            return_value=mock_connector,
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await call_rest_api(
                    prompt="test",
                    ctx=ctx,
                    url="https://api.example.com/fail",
                )
