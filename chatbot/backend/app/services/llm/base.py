from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import ClassVar

from app.schemas.ws_messages import MsgIn


class BaseLLMProvider(ABC):
    """All providers must implement these two methods."""

    # Concrete subclasses declare these as class-level constants.
    provider_name: ClassVar[str]
    default_model: ClassVar[str]
    available_models: ClassVar[list[str]]

    @classmethod
    def is_available(cls) -> bool:
        return True

    @abstractmethod
    def stream(
        self,
        messages: list[MsgIn],
        model: str,
        temperature: float,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Yield string tokens as they arrive from the LLM."""
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[MsgIn],
        model: str,
        max_tokens: int = 128,
    ) -> str:
        """Return a complete (non-streaming) response string."""
        ...
