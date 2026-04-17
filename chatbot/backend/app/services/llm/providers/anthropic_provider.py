from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider

logger = structlog.get_logger()


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"
    default_model = "claude-sonnet-4-20250514"
    available_models = [
        "claude-opus-4-20250514",
        "claude-sonnet-4-20250514",
        "claude-haiku-4-20251001",
    ]

    def __init__(self) -> None:
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.ANTHROPIC_API_KEY)

    async def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        try:
            async with self._client.messages.stream(
                model=model,
                messages=formatted,
                max_tokens=max_tokens,
                temperature=temperature,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as exc:
            logger.error("anthropic_stream_error", error=str(exc), model=model)
            raise

    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        try:
            response = await self._client.messages.create(
                model=model,
                messages=formatted,
                max_tokens=max_tokens,
            )
            return response.content[0].text
        except Exception as exc:
            logger.error("anthropic_generate_error", error=str(exc), model=model)
            raise
