"""Tests for ClarificationState in-memory paths and Redis is_pending/clear."""
from __future__ import annotations

import time

import fakeredis
import pytest

from app.agent.clarification_state import ClarificationState, _memory_store, _make_key


@pytest.fixture(autouse=True)
def clear_memory():
    _memory_store.clear()
    yield
    _memory_store.clear()


@pytest.fixture
def redis_state():
    return ClarificationState(redis_client=fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def mem_state():
    return ClarificationState(redis_client=None)


class TestInMemoryPaths:
    def test_set_and_get_in_memory(self, mem_state):
        mem_state.set_pending("u1", "c1", "Q?", ["a", "b"], "original")
        pending = mem_state.get_pending("u1", "c1")
        assert pending is not None
        assert pending["question"] == "Q?"

    def test_is_pending_true_in_memory(self, mem_state):
        mem_state.set_pending("u1", "c1", "Q?", [], "orig")
        assert mem_state.is_pending("u1", "c1") is True

    def test_is_pending_false_when_not_set(self, mem_state):
        assert mem_state.is_pending("u1", "c1") is False

    def test_clear_in_memory(self, mem_state):
        mem_state.set_pending("u1", "c1", "Q?", [], "orig")
        mem_state.clear("u1", "c1")
        assert mem_state.is_pending("u1", "c1") is False
        assert mem_state.get_pending("u1", "c1") is None

    def test_expired_entry_returns_none(self, mem_state):
        key = _make_key("u1", "c1")
        import json
        payload = json.dumps({"question": "Q?", "candidates": [], "original_query": "o", "clarification_type": "agent_question"})
        _memory_store[key] = (payload, time.monotonic() - 1)
        assert mem_state.get_pending("u1", "c1") is None

    def test_is_pending_false_for_expired_entry(self, mem_state):
        key = _make_key("u1", "c1")
        import json
        payload = json.dumps({"question": "Q?", "candidates": [], "original_query": "o", "clarification_type": "agent_question"})
        _memory_store[key] = (payload, time.monotonic() - 1)
        assert mem_state.is_pending("u1", "c1") is False

    def test_clear_no_op_when_not_set(self, mem_state):
        mem_state.clear("u1", "no_conv")  # must not raise

    def test_clarification_type_stored(self, mem_state):
        mem_state.set_pending("u1", "c1", "Q?", ["x"], "orig", clarification_type="intent_selection")
        pending = mem_state.get_pending("u1", "c1")
        assert pending["clarification_type"] == "intent_selection"


class TestRedisPaths:
    def test_is_pending_with_redis(self, redis_state):
        redis_state.set_pending("u1", "c1", "Q?", [], "orig")
        assert redis_state.is_pending("u1", "c1") is True

    def test_is_pending_false_when_not_set(self, redis_state):
        assert redis_state.is_pending("u2", "c2") is False

    def test_clear_with_redis(self, redis_state):
        redis_state.set_pending("u1", "c1", "Q?", [], "orig")
        redis_state.clear("u1", "c1")
        assert redis_state.is_pending("u1", "c1") is False

    def test_get_pending_none_after_clear(self, redis_state):
        redis_state.set_pending("u1", "c1", "Q?", [], "orig")
        redis_state.clear("u1", "c1")
        assert redis_state.get_pending("u1", "c1") is None
