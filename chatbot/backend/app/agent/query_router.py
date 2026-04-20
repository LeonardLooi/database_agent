from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from app.agent.intent_loader import IntentDefinition, YAMLIntentLoader
from app.core.config import settings

logger = structlog.get_logger()

# Data-query signal words that bypass LLM classification
_QUERY_SIGNALS = frozenset(
    [
        "select",
        "show",
        "list",
        "get",
        "fetch",
        "find",
        "count",
        "sum",
        "average",
        "avg",
        "total",
        "compare",
        "revenue",
        "sales",
        "orders",
        "customer",
        "product",
        "inventory",
        "stock",
        "report",
        "data",
        "query",
        "table",
        "database",
        "from",
        "where",
        "group",
        "join",
        "how many",
        "how much",
        "top",
        "bottom",
        "trend",
    ]
)

# Two top-scoring intents within this margin are considered ambiguous
_AMBIGUITY_MARGIN = 0.15


@dataclass
class IntentEstimationResult:
    top_intent: IntentDefinition | None
    confidence: float  # 0.0–1.0; 0.0 means no intent keyword matched at all
    is_ambiguous: bool
    candidates: list[str] = field(default_factory=list)  # "name: description" labels


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

    def estimate_intent(self, user_message: str) -> IntentEstimationResult:
        """Score each loaded intent against the user message and detect ambiguity.

        Called only after is_data_query() returns True — this is a refinement step
        to pick the best intent or detect when multiple intents are equally plausible.

        Returns:
            IntentEstimationResult with:
            - confidence == 0.0  → no intent keyword matched (generic LLM fallback)
            - is_ambiguous=True  → two or more intents score within _AMBIGUITY_MARGIN
            - is_ambiguous=False → single clear winner
        """
        lower = user_message.lower()
        intents = self._loader.all_intents()

        scored: list[tuple[float, IntentDefinition]] = []
        for intent in intents:
            kws = intent.keywords or []
            if not kws:
                continue
            hits = sum(1 for kw in kws if kw.lower() in lower)
            score = hits / len(kws)
            if score > 0:
                scored.append((score, intent))

        if not scored:
            return IntentEstimationResult(
                top_intent=None,
                confidence=0.0,
                is_ambiguous=True,
                candidates=[],
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        top_score, top_intent = scored[0]

        is_ambiguous = (
            len(scored) >= 2 and (top_score - scored[1][0]) < _AMBIGUITY_MARGIN
        )

        candidates = (
            [f"{intent.name}: {intent.description}" for _, intent in scored]
            if is_ambiguous
            else []
        )

        return IntentEstimationResult(
            top_intent=top_intent,
            confidence=top_score,
            is_ambiguous=is_ambiguous,
            candidates=candidates,
        )
