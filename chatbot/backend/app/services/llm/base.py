from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from app.schemas.ws_messages import MsgIn

if TYPE_CHECKING:
    from app.agent.skill_registry import SkillSchema
    from app.agent.tools.query_tools import AgentToolContext


class RoutingDecision(str, enum.Enum):
    CALL_SKILL = "CALL_SKILL"
    CLARIFY = "CLARIFY"
    GENERIC_ANSWER = "GENERIC_ANSWER"


@dataclass
class SkillResult:
    """Result of a YAML-driven skill execution via ``execute_skill()``.

    Intentionally separate from ``AgentLoopResult``:

    - ``SkillResult`` — YAML skill execution (NLP, document analysis, model-agnostic).
    - ``AgentLoopResult`` — database agent tool-use loop (SQL queries, data retrieval).

    Merging them would require many optional fields and obscure which flow produced
    the result.

    Attributes:
        output: Raw LLM response text.
        skill_name: Name of the YAML skill that was executed.
        model_used: Model identifier string (e.g. ``"claude-sonnet-4-20250514"``).
        confidence: Routing confidence score (0.0–1.0) from the skill-match call.
        routing_decision: Always ``RoutingDecision.CALL_SKILL`` for completed results.
        parsed_output: JSON-parsed ``output`` when the skill's ``output_format``
            specifies JSON; ``None`` when the output is not valid JSON.
    """

    output: str
    skill_name: str
    model_used: str
    confidence: float
    routing_decision: RoutingDecision
    parsed_output: dict | None = None


@dataclass
class AgentLoopResult:
    """Result of a provider's ``run_agent_loop()`` tool-use execution.

    Attributes:
        explanation: LLM-generated natural-language explanation of the query result.
        final_label: Label of the primary DataFrame in ``DataFrameStore`` to render.
            Empty string means the formatter will use the last stored label.
        sql_used: Ordered list of SQL strings executed during the loop.
        python_used: Python code string used for DataFrame operations (currently
            populated by ``combine_dataframes``).
        truncated: ``True`` if any result was capped at ``MAX_DATAFRAME_ROWS``.
        row_count: Total row count of the primary result DataFrame.
        status: One of ``"completed"``, ``"clarification_pending"``, or ``"error"``.
        error: Error message string when ``status == "error"``; empty otherwise.
    """

    explanation: str = ""
    final_label: str = ""
    sql_used: list[str] = field(default_factory=list)
    python_used: str = ""
    truncated: bool = False
    row_count: int = 0
    status: str = "completed"
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

    async def execute_skill(
        self,
        session_id: str,
        user_message: str,
        skill: "SkillSchema",
        params: dict,
        model: str,
    ) -> SkillResult:
        """Execute a YAML-driven skill using this provider's LLM. Override in subclasses."""
        raise NotImplementedError(
            f"{self.__class__.__name__} does not implement execute_skill()"
        )
