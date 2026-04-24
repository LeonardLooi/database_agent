from __future__ import annotations

import pytest

from app.services.llm.base import AgentLoopResult


def test_agent_loop_result_defaults():
    r = AgentLoopResult()
    assert r.status == "completed"
    assert r.sql_used == []
    assert r.explanation == ""
    assert r.truncated is False
    assert r.row_count == 0


def test_agent_loop_result_error_status():
    r = AgentLoopResult(status="error", error="connection refused")
    assert r.status == "error"
    assert "connection" in r.error


def test_agent_loop_result_clarification_status():
    r = AgentLoopResult(status="clarification_pending")
    assert r.status == "clarification_pending"
    assert r.explanation == ""


def test_base_provider_run_agent_loop_raises():
    """BaseLLMProvider.run_agent_loop must raise NotImplementedError."""
    import asyncio

    from app.services.llm.base import BaseLLMProvider
    from app.schemas.ws_messages import MsgIn

    class _Concrete(BaseLLMProvider):
        provider_name = "test"
        default_model = "test-model"
        available_models = ["test-model"]

        async def stream(self, messages, model, temperature, max_tokens=1024):
            yield ""

        async def generate(self, messages, model, max_tokens=128):
            return ""

    provider = _Concrete()
    with pytest.raises(NotImplementedError):
        asyncio.run(
            provider.run_agent_loop(
                [MsgIn(role="user", content="hello")], "test-model", None
            )
        )


def test_dataframe_store_round_trip(store, sample_df):
    store.store("u1", "c1", "test_label", sample_df)
    retrieved = store.retrieve("u1", "c1", "test_label")
    assert retrieved is not None
    assert len(retrieved) == len(sample_df)
    assert list(retrieved.columns) == list(sample_df.columns)


def test_dataframe_store_returns_none_for_missing(store):
    assert store.retrieve("u1", "c1", "nonexistent") is None


def test_dataframe_store_list_labels(store, sample_df):
    store.store("u1", "c1", "alpha", sample_df)
    store.store("u1", "c1", "beta", sample_df)
    labels = store.list_labels("u1", "c1")
    assert set(labels) == {"alpha", "beta"}
