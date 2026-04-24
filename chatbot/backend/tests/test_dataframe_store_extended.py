"""Extended DataFrameStore tests — in-memory paths, exists, delete, list_labels."""
from __future__ import annotations

import time

import fakeredis
import pandas as pd
import pytest

from app.agent.dataframe_store import DataFrameStore, _memory_store, _make_key


@pytest.fixture(autouse=True)
def clear_memory():
    _memory_store.clear()
    yield
    _memory_store.clear()


@pytest.fixture
def redis_store():
    return DataFrameStore(redis_client=fakeredis.FakeRedis(decode_responses=True))


@pytest.fixture
def mem_store():
    return DataFrameStore(redis_client=None)


@pytest.fixture
def sample():
    return pd.DataFrame({"id": [1, 2, 3], "val": ["a", "b", "c"]})


class TestInMemoryStore:
    def test_store_and_retrieve(self, mem_store, sample):
        mem_store.store("u1", "c1", "lbl", sample)
        df = mem_store.retrieve("u1", "c1", "lbl")
        assert df is not None
        assert list(df.columns) == list(sample.columns)
        assert len(df) == len(sample)

    def test_retrieve_missing_returns_none(self, mem_store):
        assert mem_store.retrieve("u1", "c1", "missing") is None

    def test_retrieve_expired_returns_none(self, mem_store, sample):
        key = _make_key("u1", "c1", "exp")
        _memory_store[key] = (sample.to_json(orient="split"), time.monotonic() - 1)
        assert mem_store.retrieve("u1", "c1", "exp") is None

    def test_exists_true(self, mem_store, sample):
        mem_store.store("u1", "c1", "lbl", sample)
        assert mem_store.exists("u1", "c1", "lbl") is True

    def test_exists_false_when_not_stored(self, mem_store):
        assert mem_store.exists("u1", "c1", "nope") is False

    def test_delete_removes_entry(self, mem_store, sample):
        mem_store.store("u1", "c1", "lbl", sample)
        mem_store.delete("u1", "c1", "lbl")
        assert mem_store.retrieve("u1", "c1", "lbl") is None

    def test_delete_no_op_when_not_exists(self, mem_store):
        mem_store.delete("u1", "c1", "ghost")  # must not raise

    def test_list_labels_returns_stored_labels(self, mem_store, sample):
        mem_store.store("u1", "c1", "alpha", sample)
        mem_store.store("u1", "c1", "beta", sample)
        labels = mem_store.list_labels("u1", "c1")
        assert set(labels) == {"alpha", "beta"}

    def test_list_labels_empty_when_none_stored(self, mem_store):
        assert mem_store.list_labels("u1", "c1") == []

    def test_list_labels_excludes_expired(self, mem_store, sample):
        mem_store.store("u1", "c1", "valid", sample)
        key = _make_key("u1", "c1", "expired")
        _memory_store[key] = (sample.to_json(orient="split"), time.monotonic() - 1)
        labels = mem_store.list_labels("u1", "c1")
        assert "valid" in labels
        assert "expired" not in labels


class TestRedisStore:
    def test_store_and_retrieve(self, redis_store, sample):
        redis_store.store("u1", "c1", "lbl", sample)
        df = redis_store.retrieve("u1", "c1", "lbl")
        assert df is not None
        assert len(df) == len(sample)

    def test_retrieve_missing_returns_none(self, redis_store):
        assert redis_store.retrieve("u1", "c1", "missing") is None

    def test_exists_true(self, redis_store, sample):
        redis_store.store("u1", "c1", "lbl", sample)
        assert redis_store.exists("u1", "c1", "lbl") is True

    def test_exists_false(self, redis_store):
        assert redis_store.exists("u1", "c1", "nope") is False

    def test_delete_removes_entry(self, redis_store, sample):
        redis_store.store("u1", "c1", "lbl", sample)
        redis_store.delete("u1", "c1", "lbl")
        assert redis_store.retrieve("u1", "c1", "lbl") is None

    def test_list_labels_with_redis(self, redis_store, sample):
        redis_store.store("u1", "c1", "x", sample)
        redis_store.store("u1", "c1", "y", sample)
        labels = redis_store.list_labels("u1", "c1")
        assert set(labels) == {"x", "y"}
