from __future__ import annotations

import structlog

from app.core.config import settings
from app.services.llm.base import BaseLLMProvider

logger = structlog.get_logger()

MODEL_TO_PROVIDER: dict[str, str] = {
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "o1": "openai",
    "o3-mini": "openai",
    "claude-opus-4-20250514": "anthropic",
    "claude-sonnet-4-20250514": "anthropic",
    "claude-haiku-4-20251001": "anthropic",
    "gemini-2.5-pro": "gemini",
    "gemini-2.0-flash": "gemini",
    "gemini-2.0-flash-lite": "gemini",
    "amazon.nova-pro-v1:0": "aws",
    "amazon.nova-lite-v1:0": "aws",
    "amazon.nova-micro-v1:0": "aws",
}


class LLMProviderFactory:
    _registry: dict[str, type[BaseLLMProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_cls: type[BaseLLMProvider]) -> None:
        """Register a new provider at runtime — open/closed principle."""
        cls._registry[name] = provider_cls
        logger.info("llm_provider_registered", provider=name)

    @classmethod
    def create(cls, provider_name: str | None = None) -> BaseLLMProvider:
        """Instantiate and return a provider by name.

        Args:
            provider_name: Key from the registry (e.g. "anthropic", "openai").
                Falls back to `settings.LLM_PROVIDER` when None.

        Returns:
            A fresh `BaseLLMProvider` instance for the requested provider.

        Raises:
            ValueError: If `provider_name` is not in the registry.
        """
        name = provider_name or settings.LLM_PROVIDER
        if name not in cls._registry:
            raise ValueError(
                f"Unknown LLM provider: '{name}'. Registered: {list(cls._registry)}"
            )
        return cls._registry[name]()

    @classmethod
    def resolve_provider_for_model(cls, model: str) -> str | None:
        """Look up which provider owns a given model ID.

        Args:
            model: Model identifier string (e.g. "claude-sonnet-4-20250514").

        Returns:
            Provider name string, or None if the model is not in MODEL_TO_PROVIDER.
        """
        return MODEL_TO_PROVIDER.get(model)

    @classmethod
    def available_providers(cls) -> list[str]:
        """Return a list of all registered provider names.

        Returns:
            List of provider name strings in registration order.
        """
        return list(cls._registry)

    @classmethod
    def get_providers_data(cls) -> list[dict]:
        """Return serialisable provider metadata for all available providers.

        Returns:
            List of dicts, each with keys `provider`, `models`, and `default_model`.
            Providers whose `is_available()` returns False are excluded.
        """
        result = []
        for name, provider_cls in cls._registry.items():
            if not hasattr(provider_cls, "is_available") or provider_cls.is_available():
                result.append(
                    {
                        "provider": name,
                        "models": provider_cls.available_models,
                        "default_model": provider_cls.default_model,
                    }
                )
        return result


def _register_builtin_providers() -> None:
    from app.services.llm.providers.anthropic_provider import AnthropicProvider
    from app.services.llm.providers.aws_provider import AWSBedrockProvider
    from app.services.llm.providers.gemini_provider import GeminiProvider
    from app.services.llm.providers.openai_provider import OpenAIProvider

    LLMProviderFactory._registry = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "aws": AWSBedrockProvider,
    }


_register_builtin_providers()
