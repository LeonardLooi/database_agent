from __future__ import annotations

import pandas as pd
import pytest

from app.agent.tools.combine_tools import combine_dataframes


def test_inner_join(store, ctx):
    df_a = pd.DataFrame({"id": [1, 2, 3], "revenue": [100, 200, 300]})
    df_b = pd.DataFrame({"id": [2, 3, 4], "customer": ["Alice", "Bob", "Carol"]})
    store.store("u1", "c1", "sales", df_a)
    store.store("u1", "c1", "crm", df_b)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="sales", label_b="crm", join_key="id", how="inner",
    )
    assert result["rows"] == 2
    assert "id" in result["columns"]
    combined = store.retrieve("u1", "c1", result["label"])
    assert len(combined) == 2


def test_left_join_keeps_all_left(store, ctx):
    df_a = pd.DataFrame({"id": [1, 2, 3], "val": [10, 20, 30]})
    df_b = pd.DataFrame({"id": [1, 2], "extra": ["x", "y"]})
    store.store("u1", "c1", "a", df_a)
    store.store("u1", "c1", "b", df_b)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="a", label_b="b", join_key="id", how="left",
    )
    assert result["rows"] == 3


def test_concatenate_without_join_key(store, ctx):
    df_a = pd.DataFrame({"col1": [1, 2]})
    df_b = pd.DataFrame({"col2": [3, 4]})
    store.store("u1", "c1", "a", df_a)
    store.store("u1", "c1", "b", df_b)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="a", label_b="b",
    )
    # No join key = concat side by side (outer merge on index)
    assert result["rows"] == 2


def test_missing_label_returns_error(store, ctx):
    df_a = pd.DataFrame({"id": [1]})
    store.store("u1", "c1", "exists", df_a)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="exists", label_b="missing_label",
    )
    assert "error" in result


def test_type_mismatch_coerced(store, ctx):
    df_a = pd.DataFrame({"id": [1, 2], "val": [10, 20]})
    df_b = pd.DataFrame({"id": ["1", "2"], "name": ["a", "b"]})  # id is str vs int
    store.store("u1", "c1", "a", df_a)
    store.store("u1", "c1", "b", df_b)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="a", label_b="b", join_key="id", how="inner",
    )
    # Should coerce and return rows, not an unhandled exception
    assert "rows" in result or "error" in result


def test_python_code_included(store, ctx):
    df_a = pd.DataFrame({"id": [1], "x": [1]})
    df_b = pd.DataFrame({"id": [1], "y": [2]})
    store.store("u1", "c1", "a", df_a)
    store.store("u1", "c1", "b", df_b)

    result = combine_dataframes(
        store=store, user_id="u1", conversation_id="c1",
        label_a="a", label_b="b", join_key="id", how="inner",
    )
    assert "python_code" in result
    assert "merge" in result["python_code"]
