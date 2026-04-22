from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import redis

logger = structlog.get_logger()

_KEY_PREFIX = "session_model"
_TTL_SECONDS = 86_400  # 24 hours

# In-memory fallback: {key: (model, expiry_epoch)}
_memory_store: dict[str, tuple[str, float]] = {}


def _make_key(conversation_id: str) -> str:
    return f"{_KEY_PREFIX}:{conversation_id}"


class SessionModelStore:
    """Persists the active model preference for a conversation session.

    Backed by Redis when a client is provided; falls back to an in-process dict
    when Redis is disabled (single-worker, non-persistent).
    """

    def __init__(self, redis_client: "redis.Redis | None" = None) -> None:
        self._redis = redis_client

    def set(self, conversation_id: str, model: str) -> None:
        key = _make_key(conversation_id)
        if self._redis is not None:
            self._redis.set(key, model, ex=_TTL_SECONDS)
        else:
            _memory_store[key] = (model, time.monotonic() + _TTL_SECONDS)
        logger.info("session_model_set", conversation_id=conversation_id, model=model)

    def get(self, conversation_id: str) -> str | None:
        key = _make_key(conversation_id)
        if self._redis is not None:
            raw = self._redis.get(key)
            return raw.decode() if isinstance(raw, bytes) else raw
        entry = _memory_store.get(key)
        if entry is None:
            return None
        model, expiry = entry
        if time.monotonic() > expiry:
            del _memory_store[key]
            return None
        return model
