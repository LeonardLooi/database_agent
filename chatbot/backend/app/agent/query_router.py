from __future__ import annotations

import structlog

from app.agent.intent_loader import YAMLIntentLoader
from app.core.config import settings

logger = structlog.get_logger()

# Data-query signal words that bypass LLM classification
_QUERY_SIGNALS = frozenset(
    [
        "select", "show", "list", "get", "fetch", "find", "count", "sum",
        "average", "avg", "total", "compare", "revenue", "sales", "orders",
        "customer", "product", "inventory", "stock", "report", "data",
        "query", "table", "database", "from", "where", "group", "join",
        "how many", "how much", "top", "bottom", "trend",
    ]
)


class QueryRouter:
    """Classify incoming messages as data queries or freeform chat.

    Strategy:
    1. Keyword pre-filter using YAML intent keywords + generic signal words.
       If any keyword matches, classify as data query immediately (no LLM cost).
    2. Freeform messages that contain no keywords pass through as chat.
    """

    def __init__(self) -> None:
        self._loader = YAMLIntentLoader(settings.INTENT_DIR)
        self._intent_keywords: frozenset[str] = frozenset(
            kw.lower()
            for intent in self._loader.all_intents()
            for kw in (intent.keywords or [])
        )

    def is_data_query(self, user_message: str) -> bool:
        """Return True if the message looks like a data/database query."""
        lower = user_message.lower()
        all_keywords = self._intent_keywords | _QUERY_SIGNALS
        return any(kw in lower for kw in all_keywords)
