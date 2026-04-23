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
        """Persist a pending clarification question for a conversation.

        The next inbound message for this (user, conversation) pair will be
        treated as the user's answer rather than a new question.

        Args:
            user_id: Authenticated user who was asked the question.
            conversation_id: Conversation in which clarification is pending.
            question: Text of the clarifying question shown to the user.
            candidates: Intent candidate labels presented as selectable options.
            original_query: The user's original message that triggered clarification.
            clarification_type: ``"agent_question"``, ``"intent_selection"``, or
                ``"skill_clarification"`` — controls how the next message is routed.
        """
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
        """Return the pending clarification payload, or ``None`` if none is active.

        Args:
            user_id: Authenticated user to check.
            conversation_id: Conversation to check.

        Returns:
            Dict with keys ``question``, ``candidates``, ``original_query``, and
            ``clarification_type``, or ``None`` if no clarification is pending.
        """
        key = _make_key(user_id, conversation_id)
        raw = self._redis.get(key) if self._redis is not None else self._mem_get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def is_pending(self, user_id: str, conversation_id: str) -> bool:
        """Return ``True`` if a clarification question is awaiting an answer.

        Args:
            user_id: Authenticated user to check.
            conversation_id: Conversation to check.
        """
        key = _make_key(user_id, conversation_id)
        if self._redis is not None:
            return bool(self._redis.exists(key))
        return self._mem_get(key) is not None

    def clear(self, user_id: str, conversation_id: str) -> None:
        """Delete any pending clarification for this (user, conversation) pair.

        Called immediately before routing the user's clarification answer so
        the next message is treated as a new turn.

        Args:
            user_id: Authenticated user whose clarification to clear.
            conversation_id: Conversation whose clarification to clear.
        """
        key = _make_key(user_id, conversation_id)
        if self._redis is not None:
            self._redis.delete(key)
        else:
            self._mem_delete(key)
        logger.info(
            "clarification_cleared", user_id=user_id, conversation_id=conversation_id
        )
