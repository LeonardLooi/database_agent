"""Tests for ResponseFormatter and _df_to_markdown."""
from __future__ import annotations

import fakeredis
import pandas as pd
import pytest

from app.agent.dataframe_store import DataFrameStore
from app.agent.response_formatter import ResponseFormatter, _df_to_markdown
from app.services.llm.base import AgentLoopResult


@pytest.fixture
def store():
    return DataFrameStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def formatter(store):
    return ResponseFormatter(store)


def _result(**kwargs) -> AgentLoopResult:
    defaults = dict(status="completed", explanation="Here are the results.")
    defaults.update(kwargs)
    return AgentLoopResult(**defaults)


class TestResponseFormatterBuild:
    def test_build_no_dataframe_returns_response(self, formatter):
        result = _result()
        resp = formatter.build(result, "c1", "u1", "anthropic", "claude-sonnet-4-20250514")
        assert resp.conversation_id == "c1"
        assert resp.provider == "anthropic"
        assert resp.model == "claude-sonnet-4-20250514"
        assert resp.table_md == ""
        assert resp.csv == ""

    def test_build_with_dataframe_fills_table_and_csv(self, formatter, store):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "amount": [100, 200]})
        store.store("u1", "c1", "snowflake_result", df)
        result = _result()
        resp = formatter.build(result, "c1", "u1", "anthropic", "claude-sonnet-4-20250514")
        assert "Alice" in resp.table_md
        assert "name" in resp.csv
        assert resp.row_count == 2

    def test_build_uses_final_label(self, formatter, store):
        df_a = pd.DataFrame({"x": [1]})
        df_b = pd.DataFrame({"y": [2, 3]})
        store.store("u1", "c1", "label_a", df_a)
        store.store("u1", "c1", "label_b", df_b)
        result = _result(final_label="label_b")
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.row_count == 2

    def test_build_uses_last_label_when_no_final_label(self, formatter, store):
        df = pd.DataFrame({"col": range(5)})
        store.store("u1", "c1", "only_result", df)
        result = _result(final_label=None)
        resp = formatter.build(result, "c1", "u1", "openai", "gpt-4o")
        assert resp.row_count == 5

    def test_build_empty_dataframe_skips_table(self, formatter, store):
        df = pd.DataFrame()
        store.store("u1", "c1", "empty_result", df)
        result = _result(final_label="empty_result")
        resp = formatter.build(result, "c1", "u1", "openai", "gpt-4o")
        assert resp.table_md == ""
        assert resp.csv == ""

    def test_build_truncation_flag_when_over_50_rows(self, formatter, store):
        df = pd.DataFrame({"n": range(60)})
        store.store("u1", "c1", "big_result", df)
        result = _result(final_label="big_result")
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.truncated is True
        assert resp.row_count == 60
        assert "| 0 |" in resp.table_md or "| n |" in resp.table_md

    def test_build_no_truncation_for_small_result(self, formatter, store):
        df = pd.DataFrame({"n": range(10)})
        store.store("u1", "c1", "small_result", df)
        result = _result(final_label="small_result", truncated=False)
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.truncated is False

    def test_build_sql_used_propagated(self, formatter):
        result = _result(sql_used=["SELECT 1", "SELECT 2"])
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.sql_used == ["SELECT 1", "SELECT 2"]

    def test_build_explanation_propagated(self, formatter):
        result = _result(explanation="Query returned 5 rows.")
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.explanation == "Query returned 5 rows."

    def test_build_result_truncated_flag_respected(self, formatter, store):
        df = pd.DataFrame({"n": range(10)})
        store.store("u1", "c1", "res", df)
        result = _result(final_label="res", truncated=True)
        resp = formatter.build(result, "c1", "u1", "anthropic", "m")
        assert resp.truncated is True


class TestDfToMarkdown:
    def test_empty_dataframe_returns_empty_string(self):
        assert _df_to_markdown(pd.DataFrame()) == ""

    def test_header_and_separator_present(self):
        df = pd.DataFrame({"a": [1], "b": [2]})
        md = _df_to_markdown(df)
        assert "| a | b |" in md
        assert "| --- | --- |" in md

    def test_rows_present(self):
        df = pd.DataFrame({"x": [10, 20]})
        md = _df_to_markdown(df)
        assert "| 10 |" in md
        assert "| 20 |" in md

    def test_pipe_in_cell_escaped(self):
        df = pd.DataFrame({"col": ["a|b"]})
        md = _df_to_markdown(df)
        assert "a\\|b" in md

    def test_single_row_single_col(self):
        df = pd.DataFrame({"name": ["Alice"]})
        md = _df_to_markdown(df)
        assert "| name |" in md
        assert "| Alice |" in md
