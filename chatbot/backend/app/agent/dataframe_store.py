from __future__ import annotations

import time
from io import StringIO
from typing import TYPE_CHECKING

import pandas as pd
import structlog

from app.core.config import settings

if TYPE_CHECKING:
    import redis

logger = structlog.get_logger()

_KEY_PREFIX = "df"

# In-memory fallback: {key: (serialized_json, expiry_epoch)}
_memory_store: dict[str, tuple[str, float]] = {}


def _make_key(user_id: str, conversation_id: str, label: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}:{conversation_id}:{label}"


class DataFrameStore:
    """Store for session-scoped DataFrames.

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

    def _mem_exists(self, key: str) -> bool:
        return self._mem_get(key) is not None

    def _mem_delete(self, key: str) -> None:
        _memory_store.pop(key, None)

    # ── public API ──────────────────────────────────────────────────────────

    def store(self, user_id: str, conversation_id: str, label: str, df: pd.DataFrame) -> None:
        """Serialise and persist a DataFrame under a session-scoped label.

        Args:
            user_id: Authenticated user who owns this DataFrame.
            conversation_id: Conversation in which the DataFrame was produced.
            label: Short name for this result (e.g. ``"snowflake_result"``).
            df: DataFrame to store. Serialised as JSON ``orient="split"``.
        """
        key = _make_key(user_id, conversation_id, label)
        serialized = df.to_json(orient="split")
        if self._redis is not None:
            self._redis.set(key, serialized, ex=settings.DATAFRAME_TTL_SECONDS)
        else:
            self._mem_set(key, serialized, settings.DATAFRAME_TTL_SECONDS)
        logger.debug("dataframe_stored", key=key, rows=len(df), columns=list(df.columns))

    def retrieve(self, user_id: str, conversation_id: str, label: str) -> pd.DataFrame | None:
        """Deserialise and return a stored DataFrame, or ``None`` if not found or expired.

        Args:
            user_id: Owning user.
            conversation_id: Owning conversation.
            label: Label used when the DataFrame was stored.

        Returns:
            Reconstructed ``pd.DataFrame``, or ``None`` if the key does not exist
            or its TTL has elapsed.
        """
        key = _make_key(user_id, conversation_id, label)
        raw = self._redis.get(key) if self._redis is not None else self._mem_get(key)
        if raw is None:
            logger.debug("dataframe_not_found", key=key)
            return None
        df = pd.read_json(StringIO(raw), orient="split")
        logger.debug("dataframe_retrieved", key=key, rows=len(df))
        return df

    def exists(self, user_id: str, conversation_id: str, label: str) -> bool:
        """Return ``True`` if a non-expired DataFrame exists under the given label.

        Args:
            user_id: Owning user.
            conversation_id: Owning conversation.
            label: Label to check.
        """
        key = _make_key(user_id, conversation_id, label)
        if self._redis is not None:
            return bool(self._redis.exists(key))
        return self._mem_exists(key)

    def delete(self, user_id: str, conversation_id: str, label: str) -> None:
        """Remove a stored DataFrame. No-op if the label does not exist.

        Args:
            user_id: Owning user.
            conversation_id: Owning conversation.
            label: Label of the DataFrame to remove.
        """
        key = _make_key(user_id, conversation_id, label)
        if self._redis is not None:
            self._redis.delete(key)
        else:
            self._mem_delete(key)

    def list_labels(self, user_id: str, conversation_id: str) -> list[str]:
        """Return all non-expired DataFrame labels for a conversation session.

        Args:
            user_id: Owning user.
            conversation_id: Owning conversation.

        Returns:
            List of label strings in no guaranteed order.
        """
        prefix = _make_key(user_id, conversation_id, "")
        if self._redis is not None:
            keys = self._redis.keys(_make_key(user_id, conversation_id, "*"))
        else:
            now = time.monotonic()
            keys = [k for k, (_, exp) in list(_memory_store.items()) if k.startswith(prefix) and now <= exp]
        return [k[len(prefix):] for k in keys]
