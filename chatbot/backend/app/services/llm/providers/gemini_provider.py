from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider

logger = structlog.get_logger()


class GeminiProvider(BaseLLMProvider):
    provider_name = "gemini"
    default_model = "gemini-2.0-flash"
    available_models = ["gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"]

    def __init__(self) -> None:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not configured")
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self._genai = genai

    @classmethod
    def is_available(cls) -> bool:
        return bool(settings.GOOGLE_API_KEY)

    def _to_gemini_contents(self, messages: list[MsgIn]) -> list[dict]:
        """Convert MsgIn list to Gemini content format, mapping assistant→model."""
        contents = []
        for m in messages:
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        return contents

    async def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        contents = self._to_gemini_contents(messages)
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            generation_config=self._genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        try:
            response = await gen_model.generate_content_async(contents, stream=True)
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as exc:
            logger.error("gemini_stream_error", error=str(exc), model=model)
            raise

    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        contents = self._to_gemini_contents(messages)
        gen_model = self._genai.GenerativeModel(
            model_name=model,
            generation_config=self._genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
            ),
        )
        try:
            response = await gen_model.generate_content_async(contents)
            return response.text
        except Exception as exc:
            logger.error("gemini_generate_error", error=str(exc), model=model)
            raise
