"""Extended combine_dataframes tests — all error paths and edge cases."""
from __future__ import annotations

import fakeredis
import pandas as pd
import pytest

from app.agent.dataframe_store import DataFrameStore
from app.agent.tools.combine_tools import combine_dataframes


@pytest.fixture
def store():
    return DataFrameStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


def _store_df(store, label, df):
    store.store("u1", "c1", label, df)


def _combine(store, **kwargs):
    defaults = dict(store=store, user_id="u1", conversation_id="c1")
    defaults.update(kwargs)
    return combine_dataframes(**defaults)


class TestMissingDatasets:
    def test_missing_label_a_returns_error(self, store):
        df_b = pd.DataFrame({"id": [1]})
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="missing_a", label_b="b")
        assert "error" in result
        assert "missing_a" in result["error"]

    def test_missing_label_b_returns_error(self, store):
        df_a = pd.DataFrame({"id": [1]})
        _store_df(store, "a", df_a)
        result = _combine(store, label_a="a", label_b="missing_b")
        assert "error" in result
        assert "missing_b" in result["error"]

    def test_both_missing_returns_label_a_error(self, store):
        result = _combine(store, label_a="no_a", label_b="no_b")
        assert "error" in result
        assert "no_a" in result["error"]


class TestEmptyDatasets:
    def test_empty_label_a_returns_error(self, store):
        _store_df(store, "empty_a", pd.DataFrame())
        _store_df(store, "b", pd.DataFrame({"id": [1]}))
        result = _combine(store, label_a="empty_a", label_b="b")
        assert "error" in result
        assert "0 rows" in result["error"]

    def test_empty_label_b_returns_error(self, store):
        _store_df(store, "a", pd.DataFrame({"id": [1]}))
        _store_df(store, "empty_b", pd.DataFrame())
        result = _combine(store, label_a="a", label_b="empty_b")
        assert "error" in result
        assert "0 rows" in result["error"]


class TestMissingJoinKey:
    def test_join_key_not_in_label_a_returns_error(self, store):
        df_a = pd.DataFrame({"x": [1, 2]})
        df_b = pd.DataFrame({"id": [1, 2], "y": [3, 4]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id")
        assert "error" in result
        assert "id" in result["error"]

    def test_join_key_not_in_label_b_returns_error(self, store):
        df_a = pd.DataFrame({"id": [1, 2], "x": [3, 4]})
        df_b = pd.DataFrame({"y": [1, 2]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id")
        assert "error" in result
        assert "id" in result["error"]


class TestTypeMismatch:
    def test_type_mismatch_coerced_with_warning(self, store):
        # Use non-numeric strings so pd.read_json doesn't coerce them back to int64
        df_a = pd.DataFrame({"id": [1, 2, 3], "val_a": ["x", "y", "z"]})
        df_b = pd.DataFrame({"id": ["id1", "id2", "id4"], "val_b": ["p", "q", "r"]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id", how="inner")
        assert "error" not in result
        assert result["type_warning"] != ""
        assert "Coerced" in result["type_warning"]


class TestTruncation:
    def test_large_result_truncated(self, store, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "MAX_DATAFRAME_ROWS", 3)
        df_a = pd.DataFrame({"id": [1, 2, 3, 4, 5], "a": range(5)})
        df_b = pd.DataFrame({"id": [1, 2, 3, 4, 5], "b": range(5)})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id")
        assert result["truncated"] is True
        assert result["rows"] == 3


class TestPythonCode:
    def test_python_code_includes_merge(self, store):
        df_a = pd.DataFrame({"id": [1], "v": [1]})
        df_b = pd.DataFrame({"id": [1], "w": [2]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id")
        assert "merge" in result["python_code"]

    def test_python_code_includes_concat_when_no_key(self, store):
        df_a = pd.DataFrame({"x": [1]})
        df_b = pd.DataFrame({"y": [2]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b")
        assert "concat" in result["python_code"]


class TestOuterJoin:
    def test_outer_join_all_rows(self, store):
        df_a = pd.DataFrame({"id": [1, 2], "a": [10, 20]})
        df_b = pd.DataFrame({"id": [2, 3], "b": [30, 40]})
        _store_df(store, "a", df_a)
        _store_df(store, "b", df_b)
        result = _combine(store, label_a="a", label_b="b", join_key="id", how="outer")
        assert result["rows"] == 3
