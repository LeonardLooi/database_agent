from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from app.schemas.ws_messages import MsgIn

if TYPE_CHECKING:
    from app.agent.tools.query_tools import AgentToolContext


@dataclass
class AgentLoopResult:
    explanation: str = ""
    final_label: str = ""
    sql_used: list[str] = field(default_factory=list)
    python_used: str = ""
    truncated: bool = False
    row_count: int = 0
    status: str = "completed"  # "completed" | "clarification_pending" | "error"
    error: str = ""


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

    async def run_agent_loop(
        self,
        messages: list[MsgIn],
        model: str,
        ctx: "AgentToolContext",
    ) -> AgentLoopResult:
        """Run provider-native agent loop with tool use. Override in subclasses."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement run_agent_loop()"
        )
