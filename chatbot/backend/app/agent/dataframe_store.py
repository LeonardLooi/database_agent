from __future__ import annotations

from io import StringIO

import pandas as pd
import redis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

_KEY_PREFIX = "df"


def _make_key(user_id: str, conversation_id: str, label: str) -> str:
    return f"{_KEY_PREFIX}:{user_id}:{conversation_id}:{label}"


class DataFrameStore:
    """Redis-backed store for session-scoped DataFrames.

    Key pattern : df:{user_id}:{conversation_id}:{label}
    TTL         : settings.DATAFRAME_TTL_SECONDS (default 3600)
    Serialization: df.to_json(orient='split') — avoids pickle security risk
    """

    def __init__(self, redis_client: redis.Redis | None = None) -> None:
        self._redis = redis_client or redis.from_url(
            settings.REDIS_URL, decode_responses=True
        )

    def store(
        self,
        user_id: str,
        conversation_id: str,
        label: str,
        df: pd.DataFrame,
    ) -> None:
        key = _make_key(user_id, conversation_id, label)
        serialized = df.to_json(orient="split")
        self._redis.set(key, serialized, ex=settings.DATAFRAME_TTL_SECONDS)
        logger.debug(
            "dataframe_stored",
            key=key,
            rows=len(df),
            columns=list(df.columns),
        )

    def retrieve(
        self, user_id: str, conversation_id: str, label: str
    ) -> pd.DataFrame | None:
        key = _make_key(user_id, conversation_id, label)
        raw = self._redis.get(key)
        if raw is None:
            logger.debug("dataframe_not_found", key=key)
            return None
        df = pd.read_json(StringIO(raw), orient="split")
        logger.debug("dataframe_retrieved", key=key, rows=len(df))
        return df

    def exists(self, user_id: str, conversation_id: str, label: str) -> bool:
        key = _make_key(user_id, conversation_id, label)
        return bool(self._redis.exists(key))

    def delete(self, user_id: str, conversation_id: str, label: str) -> None:
        key = _make_key(user_id, conversation_id, label)
        self._redis.delete(key)

    def list_labels(self, user_id: str, conversation_id: str) -> list[str]:
        pattern = _make_key(user_id, conversation_id, "*")
        keys = self._redis.keys(pattern)
        prefix = _make_key(user_id, conversation_id, "")
        return [k[len(prefix):] for k in keys]
