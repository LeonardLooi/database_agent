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

    # ── function_calling agent loop ───────────────────────────────────────────

    async def run_agent_loop(
        self,
        messages: list[MsgIn],
        model: str,
        ctx: "AgentToolContext",
    ) -> AgentLoopResult:
        from app.agent.shared_toolkit import SharedToolkit
        from app.core.config import settings as cfg

        toolkit = SharedToolkit()
        tools = toolkit.get_openai_tools()
        system = toolkit.intents_as_system_context()
        # o1/o3 don't support system role — use developer role instead
        system_role = "developer" if model.startswith(("o1", "o3")) else "system"
        loop_messages: list[dict] = [{"role": system_role, "content": system}]
        loop_messages += [{"role": m.role, "content": m.content} for m in messages]
        result = AgentLoopResult()
        sql_used: list[str] = []
        supports_temperature = not model.startswith(("o1", "o3"))

        try:
            for _ in range(cfg.MAX_TOOL_CALLS):
                kwargs: dict = {
                    "model": model,
                    "messages": loop_messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "max_completion_tokens": 4096,
                }
                if supports_temperature:
                    kwargs["temperature"] = 0.0

                response = await self._client.chat.completions.create(**kwargs)
                msg = response.choices[0].message

                if msg.content:
                    result.explanation = msg.content

                if not msg.tool_calls:
                    break

                # Append assistant message with tool_calls
                loop_messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                # Execute each tool call
                for tc in msg.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_args = {}

                    logger.info(
                        "openai_tool_call",
                        tool=tool_name,
                        user_id=ctx.user_id,
                    )

                    try:
                        tool_output = await toolkit.dispatch(tool_name, tool_args, ctx)
                    except Exception as tool_exc:
                        logger.error(
                            "openai_tool_error",
                            tool=tool_name,
                            error=str(tool_exc),
                        )
                        tool_output = {"error": str(tool_exc)}

                    if isinstance(tool_output, dict) and "sql" in tool_output:
                        sql_used.append(tool_output["sql"])

                    loop_messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(tool_output),
                    })

                if ctx.clarification_state.is_pending(ctx.user_id, ctx.conversation_id):
                    result.status = "clarification_pending"
                    return result

            result.sql_used = sql_used
            result.status = "completed"

        except Exception as exc:
            logger.error(
                "openai_agent_loop_error",
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
        from app.agent.skill_prompt_builder import SkillPromptBuilder
        from app.services.llm.base import RoutingDecision, SkillResult

        system_prompt = SkillPromptBuilder.build(skill, params)
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                max_completion_tokens=2048,
            )
            output = response.choices[0].message.content or ""
        except Exception as exc:
            logger.error("openai_execute_skill_error", error=str(exc), skill=skill.name)
            raise

        try:
            parsed: dict | None = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            parsed = None

        return SkillResult(
            output=output,
            skill_name=skill.name,
            model_used=model,
            confidence=1.0,
            routing_decision=RoutingDecision.CALL_SKILL,
            parsed_output=parsed,
        )
