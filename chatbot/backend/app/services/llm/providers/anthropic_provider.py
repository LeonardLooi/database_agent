from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult, BaseLLMProvider

if TYPE_CHECKING:
    from app.agent.skill_registry import SkillSchema
    from app.agent.tools.query_tools import AgentToolContext
    from app.services.llm.base import SkillResult

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

    # ── tool_use agent loop ───────────────────────────────────────────────────

    async def run_agent_loop(
        self,
        messages: list[MsgIn],
        model: str,
        ctx: "AgentToolContext",
    ) -> AgentLoopResult:
        from app.agent.shared_toolkit import SharedToolkit
        from app.core.config import settings as cfg

        toolkit = SharedToolkit()
        tools = toolkit.get_anthropic_tools()
        system = toolkit.intents_as_system_context()
        loop_messages = [{"role": m.role, "content": m.content} for m in messages]
        result = AgentLoopResult()
        sql_used: list[str] = []

        try:
            for _ in range(cfg.MAX_TOOL_CALLS):
                response = await self._client.messages.create(
                    model=model,
                    system=system,
                    messages=loop_messages,
                    tools=tools,
                    max_tokens=4096,
                )

                # Collect any text content
                text_parts = [b.text for b in response.content if b.type == "text"]
                if text_parts:
                    result.explanation = " ".join(text_parts)

                if response.stop_reason != "tool_use":
                    break

                # Process tool calls
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    tool_name = block.name
                    tool_args = block.input

                    logger.info(
                        "anthropic_tool_call",
                        tool=tool_name,
                        user_id=ctx.user_id,
                    )

                    try:
                        tool_output = await toolkit.dispatch(tool_name, tool_args, ctx)
                    except Exception as tool_exc:
                        logger.error(
                            "anthropic_tool_error",
                            tool=tool_name,
                            error=str(tool_exc),
                        )
                        tool_output = {"error": str(tool_exc)}

                    # Track SQL from query tools
                    if isinstance(tool_output, dict) and "sql" in tool_output:
                        sql_used.append(tool_output["sql"])

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(tool_output),
                    })

                # Append assistant turn + tool results to loop
                loop_messages.append({"role": "assistant", "content": response.content})
                loop_messages.append({"role": "user", "content": tool_results})

                if ctx.clarification_state.is_pending(ctx.user_id, ctx.conversation_id):
                    result.status = "clarification_pending"
                    return result

            result.sql_used = sql_used
            result.status = "completed"

        except Exception as exc:
            logger.error(
                "anthropic_agent_loop_error",
                error=str(exc),
                model=model,
                user_id=ctx.user_id,
            )
            result.status = "error"
            result.error = str(exc)

        return result

    # ── skill execution ───────────────────────────────────────────────────────

    async def execute_skill(
        self,
        session_id: str,
        user_message: str,
        skill: "SkillSchema",
        params: dict,
        model: str,
    ) -> "SkillResult":
        import json as _json

        from app.agent.skill_prompt_builder import SkillPromptBuilder
        from app.services.llm.base import RoutingDecision, SkillResult

        system_prompt = SkillPromptBuilder.build(skill, params)
        try:
            response = await self._client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=2048,
            )
            output = response.content[0].text if response.content else ""
        except Exception as exc:
            logger.error("anthropic_execute_skill_error", error=str(exc), skill=skill.name)
            raise

        try:
            parsed: dict | None = _json.loads(output)
        except (ValueError, _json.JSONDecodeError):
            parsed = None

        return SkillResult(
            output=output,
            skill_name=skill.name,
            model_used=model,
            confidence=1.0,
            routing_decision=RoutingDecision.CALL_SKILL,
            parsed_output=parsed,
        )
