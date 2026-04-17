from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog

from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import LLMProviderFactory

logger = structlog.get_logger()


class LLMService:
    """Thin orchestration layer — callers never reference concrete providers directly."""

    def __init__(self, provider: BaseLLMProvider | None = None) -> None:
        self.provider = provider or LLMProviderFactory.create()

    async def stream(
        self,
        messages: list[MsgIn],
        model: str | None,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        resolved_model = model or self.provider.default_model
        logger.info(
            "llm_stream_start",
            provider=self.provider.provider_name,
            model=resolved_model,
            message_count=len(messages),
        )
        async for token in self.provider.stream(messages, resolved_model, temperature, max_tokens):
            yield token

    async def generate_title(self, content: str) -> str:
        prompt = [
            MsgIn(
                role="user",
                content=f"Reply with ONLY a 4-word title for this message. No punctuation. Message: {content[:500]}",
            )
        ]
        fast_model = self.provider.available_models[-1]
        try:
            title = await self.provider.generate(prompt, model=fast_model, max_tokens=20)
            return title.strip().strip('"').strip("'")
        except Exception as exc:
            logger.error("title_generation_failed", error=str(exc))
            return "New Conversation"
