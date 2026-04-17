from __future__ import annotations

from collections.abc import AsyncGenerator

import boto3  # noqa: F401 — used in is_available and Session construction
import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider

logger = structlog.get_logger()


class AWSBedrockProvider(BaseLLMProvider):
    provider_name = "aws"
    default_model = "amazon.nova-lite-v1:0"
    available_models = [
        "amazon.nova-pro-v1:0",
        "amazon.nova-lite-v1:0",
        "amazon.nova-micro-v1:0",
    ]

    def __init__(self) -> None:
        try:
            from strands.models.bedrock import BedrockModel
        except ImportError as exc:
            raise RuntimeError("strands-agents is required: pip install strands-agents") from exc

        session = boto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
            aws_session_token=settings.AWS_SESSION_TOKEN or None,
            region_name=settings.AWS_REGION,
        )
        self._bedrock = BedrockModel(boto_session=session, model_id=self.default_model)

    @classmethod
    def is_available(cls) -> bool:
        try:
            import boto3 as _b  # noqa: F401
            from strands.models.bedrock import BedrockModel as _m  # noqa: F401
            _ = _b, _m  # suppress "not accessed" warning
            return bool(settings.AWS_REGION)
        except ImportError:
            return False

    @staticmethod
    def _format_messages(messages: list[MsgIn]) -> list[dict]:
        return [{"role": m.role, "content": [{"text": m.content}]} for m in messages]

    async def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        self._bedrock.update_config(model_id=model, temperature=temperature, max_tokens=max_tokens)
        formatted = self._format_messages(messages)
        try:
            async for event in self._bedrock.stream(formatted):  # type: ignore[arg-type]
                if "contentBlockDelta" in event:
                    delta = event["contentBlockDelta"].get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield text
        except Exception as exc:
            logger.error("aws_stream_error", error=str(exc), model=model)
            raise

    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        parts: list[str] = []
        async for token in self.stream(messages, model, temperature=0.0, max_tokens=max_tokens):
            parts.append(token)
        return "".join(parts)
