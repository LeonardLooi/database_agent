from __future__ import annotations

import json

import redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_KEY_PREFIX = "clarification"


def _make_key(user_id: str, conversation_id: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}:{conversation_id}"


class ClarificationState:
    """Redis-backed state for pausing an agent loop mid-execution to ask the user
    a clarifying question and resuming when they respond.

    Key pattern : clarification:{user_id}:{conversation_id}
    TTL         : settings.CLARIFICATION_TTL_SECONDS (default 300 — 5 min timeout)
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client or redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    def set_pending(
        self,
        user_id: str,
        conversation_id: str,
        question: str,
        candidates: list[str],
        original_query: str,
    ) -> None:
        key = _make_key(user_id, conversation_id)
        payload = {
            "question": question,
            "candidates": candidates,
            "original_query": original_query,
        }
        self._redis.set(
            key, json.dumps(payload), ex=settings.CLARIFICATION_TTL_SECONDS
        )
        logger.info(
            "clarification_pending",
            user_id=user_id,
            conversation_id=conversation_id,
        )

    def get_pending(
        self, user_id: str, conversation_id: str
    ) -> dict | None:
        key = _make_key(user_id, conversation_id)
        raw = self._redis.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def is_pending(self, user_id: str, conversation_id: str) -> bool:
        key = _make_key(user_id, conversation_id)
        return bool(self._redis.exists(key))

    def clear(self, user_id: str, conversation_id: str) -> None:
        key = _make_key(user_id, conversation_id)
        self._redis.delete(key)
        logger.info(
            "clarification_cleared",
            user_id=user_id,
            conversation_id=conversation_id,
        )
