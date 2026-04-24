"""Tests for SessionModelStore — Redis-backed and in-memory paths."""
from __future__ import annotations

import time

import fakeredis
import pytest

from app.agent.session_model_store import SessionModelStore, _memory_store, _make_key


@pytest.fixture(autouse=True)
def clear_memory_store():
    _memory_store.clear()
    yield
    _memory_store.clear()


@pytest.fixture
def redis_store():
    return SessionModelStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def mem_store():
    return SessionModelStore(redis_client=None)


class TestRedisBackedStore:
    def test_set_and_get(self, redis_store):
        redis_store.set("conv-1", "gpt-4o")
        assert redis_store.get("conv-1") == "gpt-4o"

    def test_get_returns_none_when_not_set(self, redis_store):
        assert redis_store.get("nonexistent-conv") is None

    def test_set_overwrites_previous(self, redis_store):
        redis_store.set("conv-1", "gpt-4o")
        redis_store.set("conv-1", "claude-sonnet-4-20250514")
        assert redis_store.get("conv-1") == "claude-sonnet-4-20250514"

    def test_different_conversations_isolated(self, redis_store):
        redis_store.set("conv-a", "gpt-4o")
        redis_store.set("conv-b", "claude-sonnet-4-20250514")
        assert redis_store.get("conv-a") == "gpt-4o"
        assert redis_store.get("conv-b") == "claude-sonnet-4-20250514"

    def test_bytes_value_decoded(self):
        raw_redis = fakeredis.FakeRedis()  # bytes mode
        store = SessionModelStore(redis_client=raw_redis)
        raw_redis.set("session_model:conv-x", b"gpt-4o-mini")
        assert store.get("conv-x") == "gpt-4o-mini"


class TestInMemoryStore:
    def test_set_and_get(self, mem_store):
        mem_store.set("conv-1", "gpt-4o")
        assert mem_store.get("conv-1") == "gpt-4o"

    def test_get_returns_none_when_not_set(self, mem_store):
        assert mem_store.get("nonexistent-conv") is None

    def test_set_overwrites_previous(self, mem_store):
        mem_store.set("conv-1", "gpt-4o")
        mem_store.set("conv-1", "claude-haiku-4-20251001")
        assert mem_store.get("conv-1") == "claude-haiku-4-20251001"

    def test_expired_entry_returns_none(self, mem_store):
        key = _make_key("conv-expire")
        _memory_store[key] = ("gpt-4o", time.monotonic() - 1)
        assert mem_store.get("conv-expire") is None

    def test_expired_entry_removed_from_store(self, mem_store):
        key = _make_key("conv-expire")
        _memory_store[key] = ("gpt-4o", time.monotonic() - 1)
        mem_store.get("conv-expire")
        assert key not in _memory_store

    def test_not_yet_expired_entry_returned(self, mem_store):
        mem_store.set("conv-valid", "gemini-2.5-flash")
        assert mem_store.get("conv-valid") == "gemini-2.5-flash"
