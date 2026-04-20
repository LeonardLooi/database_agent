from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

import structlog

from app.core.config import settings

if TYPE_CHECKING:
    import redis

logger = structlog.get_logger()

_KEY_PREFIX = "clarification"

# In-memory fallback: {key: (payload_json, expiry_epoch)}
_memory_store: dict[str, tuple[str, float]] = {}


def _make_key(user_id: str, conversation_id: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}:{conversation_id}"


class ClarificationState:
    """State store for mid-loop clarification questions.

    Backed by Redis when a client is provided; falls back to an in-process dict
    (single-worker, non-persistent) when Redis is disabled.
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client

    # ── internal helpers ────────────────────────────────────────────────────

    def _mem_set(self, key: str, value: str, ttl: int) -> None:
        _memory_store[key] = (value, time.monotonic() + ttl)

    def _mem_get(self, key: str) -> str | None:
        entry = _memory_store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() > expiry:
            del _memory_store[key]
            return None
        return value

    def _mem_delete(self, key: str) -> None:
        _memory_store.pop(key, None)

    # ── public API ──────────────────────────────────────────────────────────

    def set_pending(
        self,
        user_id: str,
        conversation_id: str,
        question: str,
        candidates: list[str],
        original_query: str,
        clarification_type: str = "agent_question",
    ) -> None:
        key = _make_key(user_id, conversation_id)
        payload = json.dumps(
            {
                "question": question,
                "candidates": candidates,
                "original_query": original_query,
                "clarification_type": clarification_type,
            }
        )
        if self._redis is not None:
            self._redis.set(key, payload, ex=settings.CLARIFICATION_TTL_SECONDS)
        else:
            self._mem_set(key, payload, settings.CLARIFICATION_TTL_SECONDS)
        logger.info(
            "clarification_pending", user_id=user_id, conversation_id=conversation_id
        )

    def get_pending(self, user_id: str, conversation_id: str) -> dict | None:
        key = _make_key(user_id, conversation_id)
        raw = self._redis.get(key) if self._redis is not None else self._mem_get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def is_pending(self, user_id: str, conversation_id: str) -> bool:
        key = _make_key(user_id, conversation_id)
        if self._redis is not None:
            return bool(self._redis.exists(key))
        return self._mem_get(key) is not None

    def clear(self, user_id: str, conversation_id: str) -> None:
        key = _make_key(user_id, conversation_id)
        if self._redis is not None:
            self._redis.delete(key)
        else:
            self._mem_delete(key)
        logger.info(
            "clarification_cleared", user_id=user_id, conversation_id=conversation_id
        )
