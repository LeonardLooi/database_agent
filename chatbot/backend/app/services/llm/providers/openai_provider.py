from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider

logger = structlog.get_logger()


class OpenAIProvider(BaseLLMProvider):
    provider_name = "openai"
    default_model = "gpt-4o"
    available_models = ["gpt-4o", "gpt-4o-mini", "o1", "o3-mini"]

    def __init__(self) -> None:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.OPENAI_API_KEY)

    async def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        # o1/o3 series does not support temperature or streaming the same way
        supports_temperature = not model.startswith(("o1", "o3"))
        try:
            kwargs: dict = {
                "model": model,
                "messages": formatted,
                "max_completion_tokens": max_tokens,
                "stream": True,
            }
            if supports_temperature:
                kwargs["temperature"] = temperature

            stream = await self._client.chat.completions.create(**kwargs)
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as exc:
            logger.error("openai_stream_error", error=str(exc), model=model)
            raise

    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=formatted,
                max_completion_tokens=max_tokens,
                stream=False,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("openai_generate_error", error=str(exc), model=model)
            raise
