# Agentic AI LLM Routing & Multi-Provider Management

Multi-provider routing, cost calculation, fallback chains, and prompt caching.

## Model Selection Matrix

### Chat Models

| Provider | Model | Best For | Cost (1M in/out) | Context | Speed |
|----------|-------|----------|-------------------|---------|-------|
| **Anthropic** | claude-opus-4-6 | Complex reasoning, agents, code | $5/$25 | 200k (1M beta) | Slow |
| Anthropic | claude-sonnet-4-5-20250929 | Balanced quality/cost | $3/$15 | 200k (1M beta) | Medium |
| Anthropic | claude-haiku-4-5-20251001 | Fast, cheap tasks | $1/$5 | 200k | Fast |
| **OpenAI** | gpt-5.2 | Flagship coding, agentic | $1.75/$14 | 400k | Medium |
| OpenAI | gpt-4.1 | Long-context, tool calling | $2/$8 | 1M | Medium |
| OpenAI | gpt-4.1-mini | Fast, cheap, tool calling | $0.40/$1.60 | 1M | Fast |
| OpenAI | gpt-4o-mini | Legacy fast/cheap tasks | $0.15/$0.60 | 128k | Fast |
| **Google** | gemini-3.1-pro | Best multimodal, agentic | $2/$12 | 1M | Medium |
| Google | gemini-3.1-flash | Frontier speed, reasoning | $0.50/$3 | 1M | Fast |
| Google | gemini-3.1-flash | Hybrid reasoning, thinking | $0.30/$2.50 | 1M | Fast |

### Embeddings

| Provider | Model | Dimensions | Cost (1M tokens) | Best For |
|----------|-------|------------|-------------------|----------|
| OpenAI | text-embedding-3-large | 3072 | $0.13 | High quality |
| OpenAI | text-embedding-3-small | 1536 | $0.02 | Cost-effective |
| Google | gemini-embedding-001 | 3072 | $0.15 | SOTA multilingual |
| Google | text-embedding-004 | 768 | ~$0.025/1K chars | Legacy (deprecated Jan 2026) |

### Rerankers

| Provider | Model | Cost | Best For |
|----------|-------|------|----------|
| Cohere | rerank-v3.5 | $2/1K searches | General reranking, 100+ langs |
| Jina | jina-reranker-v3 | Per-token | Listwise SOTA, 131K context |
| Jina | jina-reranker-v2-base-multilingual | Per-token | Multilingual, agentic RAG |

## LLM Provider Factory

**File:** `src/<service>/llm/providers.py`

```python
from __future__ import annotations

from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from ..core.config import settings
from ..core.exceptions import LLMProviderError
from ..core.logging import get_logger

logger = get_logger(__name__)

ProviderName = Literal["anthropic", "openai"]
ModelTier = Literal["fast", "balanced", "powerful"]

# Model mappings per tier
MODEL_TIERS: dict[ModelTier, dict[ProviderName, str]] = {
    "fast": {
        "anthropic": "claude-haiku-3-5-20241022",
        "openai": "gpt-4o-mini",
    },
    "balanced": {
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
    },
    "powerful": {
        "anthropic": "claude-opus-4-20250514",
        "openai": "gpt-4o",
    },
}


class LLMProviderFactory:
    """Factory for creating and managing LLM provider instances.

    Features:
    - Centralized configuration (temperature, max_tokens, etc.)
    - Provider fallback chains
    - Model tier selection (fast/balanced/powerful)
    """

    def __init__(self) -> None:
        self._providers: dict[str, BaseChatModel] = {}

    def get_default(self) -> BaseChatModel:
        """Get the default LLM provider configured in settings."""
        return self.get_model(settings.default_model, temperature=settings.default_temperature)

    def get(self, provider: ProviderName, tier: ModelTier = "balanced") -> BaseChatModel:
        """Get an LLM by provider and tier."""
        model_name = MODEL_TIERS[tier][provider]
        return self.get_model(model_name, temperature=settings.default_temperature)

    def get_model(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        **kwargs,
    ) -> BaseChatModel:
        """Get or create a specific model instance."""
        cache_key = f"{model}-{temperature}-{max_tokens}"

        if cache_key not in self._providers:
            self._providers[cache_key] = self._create_provider(model, temperature, max_tokens, **kwargs)
            logger.info("llm_provider_created", model=model, temperature=temperature)

        return self._providers[cache_key]

    def _create_provider(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        **kwargs,
    ) -> BaseChatModel:
        """Create a new LLM provider instance."""
        if "claude" in model:
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                anthropic_api_key=settings.anthropic_api_key,
                **kwargs,
            )
        elif "gpt" in model:
            if not settings.openai_api_key:
                raise LLMProviderError("OpenAI API key not configured")
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=settings.openai_api_key,
                **kwargs,
            )
        else:
            raise LLMProviderError(f"Unknown model: {model}")

    def get_fallback_chain(self, tiers: list[tuple[ProviderName, ModelTier]] | None = None) -> BaseChatModel:
        """Create a model with fallback chain.

        Default chain: anthropic/balanced → openai/balanced → anthropic/fast
        """
        if tiers is None:
            tiers = [("anthropic", "balanced"), ("openai", "balanced"), ("anthropic", "fast")]

        primary = self.get(tiers[0][0], tiers[0][1])
        fallbacks = [self.get(p, t) for p, t in tiers[1:]]

        return primary.with_fallbacks(fallbacks)
```

## Multi-Provider Router

Route requests to different models based on task complexity.

```python
from pydantic import BaseModel, Field
from typing import Literal


class TaskComplexity(BaseModel):
    """Classify task complexity for model routing."""
    complexity: Literal["simple", "moderate", "complex"] = Field(
        description="simple=factual/short, moderate=reasoning/analysis, complex=multi-step/creative"
    )


class MultiProviderRouter:
    """Route requests to appropriate models based on complexity."""

    def __init__(self, provider_factory: LLMProviderFactory):
        self._factory = provider_factory
        # Use cheap model for classification
        self._classifier = provider_factory.get("anthropic", "fast")

    async def route(self, messages: list) -> BaseChatModel:
        """Classify and route to the best model for the task."""
        classifier = self._classifier.with_structured_output(TaskComplexity)
        result = await classifier.ainvoke([
            {"role": "system", "content": "Classify the complexity of this request."},
            messages[-1],
        ])

        tier_map: dict[str, ModelTier] = {
            "simple": "fast",
            "moderate": "balanced",
            "complex": "powerful",
        }

        tier = tier_map[result.complexity]
        model = self._factory.get("anthropic", tier)
        logger.info("model_routed", complexity=result.complexity, tier=tier)
        return model
```

## Cost Estimation Calculator

```python
# Cost per 1M tokens (input, output) as of 2025
COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-opus-4-20250514": (15.0, 75.0),
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-haiku-3-5-20241022": (0.80, 4.0),
    "gpt-4o": (2.50, 10.0),
    "gpt-4o-mini": (0.15, 0.60),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost for a single LLM call.

    Returns:
        Estimated cost in USD.
    """
    if model not in COST_TABLE:
        logger.warning("unknown_model_cost", model=model)
        return 0.0

    input_rate, output_rate = COST_TABLE[model]
    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return round(cost, 6)


def estimate_session_cost(model: str, turns: int, avg_input: int = 1000, avg_output: int = 500) -> float:
    """Estimate cost for a multi-turn session."""
    total_input = sum(avg_input * (i + 1) for i in range(turns))  # Accumulating context
    total_output = avg_output * turns
    return estimate_cost(model, total_input, total_output)
```

## Prompt Caching (Anthropic)

Reduce costs by caching long system prompts.

```python
from langchain_core.messages import SystemMessage


def create_cached_system_prompt(content: str) -> SystemMessage:
    """Create a system message with Anthropic prompt caching.

    Prompt caching reduces cost by 90% for repeated system prompts.
    The cache_control header tells Anthropic to cache this content.
    """
    return SystemMessage(
        content=[
            {
                "type": "text",
                "text": content,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    )


# Usage in agent node
SYSTEM_PROMPT = """You are an expert assistant with access to the following tools...
[Long detailed system prompt with tool descriptions, rules, examples]
"""

cached_prompt = create_cached_system_prompt(SYSTEM_PROMPT)

# First call: full cost, caches the system prompt
# Subsequent calls: 90% cheaper for the cached portion
messages = [cached_prompt, *state["messages"]]
response = await llm.ainvoke(messages)
```

## Provider Fallback with Circuit Breaker

```python
import time
from dataclasses import dataclass, field


@dataclass
class CircuitBreaker:
    """Simple circuit breaker for LLM providers."""

    failure_threshold: int = 3
    recovery_timeout: float = 60.0  # seconds
    _failures: int = 0
    _last_failure: float = 0.0
    _state: str = "closed"  # closed, open, half-open

    def can_execute(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.time() - self._last_failure > self.recovery_timeout:
                self._state = "half-open"
                return True
            return False
        return True  # half-open: allow one attempt

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        self._last_failure = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "open"
            logger.warning("circuit_breaker_open", failures=self._failures)
```

## Key Rules

| Rule | Standard |
|------|----------|
| Model selection | Use cheapest model that meets quality requirements |
| Temperature | `0` for factual tasks, `0.7` only for creative |
| Fallbacks | Always configure at least one fallback provider |
| Cost tracking | Log token usage for every LLM call |
| Caching | Use prompt caching for long system prompts |
| Instantiation | Factory function only — never `ChatAnthropic()` inline in nodes |
| Circuit breaker | Use for all external LLM calls |
