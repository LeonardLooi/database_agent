from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import structlog

from app.core.config import settings
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult, BaseLLMProvider

if TYPE_CHECKING:
    from app.agent.tools.query_tools import AgentToolContext

logger = structlog.get_logger()

# ContextVar used to pass AgentToolContext into ADK tool functions without
# changing their signatures (ADK wraps them as FunctionTool).
_agent_ctx_var: ContextVar[AgentToolContext | None] = ContextVar(
    "_agent_ctx_var", default=None
)


def _make_adk_tool_wrapper(fn: Any, toolkit: Any) -> Any:
    """Wrap a query_tool async function so it pulls ctx from ContextVar."""
    import functools

    @functools.wraps(fn)
    async def wrapper(**kwargs: Any) -> Any:
        ctx = _agent_ctx_var.get()
        if ctx is None:
            raise RuntimeError("ADK tool called without AgentToolContext set")
        return await toolkit.dispatch(fn.__name__, kwargs, ctx)

    return wrapper


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

    # ── freeform helpers (google-generativeai) ────────────────────────────────

    def _to_gemini_contents(self, messages: list[MsgIn]) -> list[dict]:
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

    # ── ADK agent loop ────────────────────────────────────────────────────────

    async def run_agent_loop(
        self,
        messages: list[MsgIn],
        model: str,
        ctx: "AgentToolContext",
    ) -> AgentLoopResult:
        try:
            from google.adk.agents import LlmAgent
            from google.adk.runners import Runner
            from google.adk.sessions import InMemorySessionService
            from google.adk.tools import FunctionTool
        except ImportError as exc:
            raise RuntimeError("google-adk is required: pip install google-adk") from exc

        from app.agent.shared_toolkit import SharedToolkit

        toolkit = SharedToolkit()

        # Build ADK FunctionTools with ContextVar injection
        adk_tools = [
            FunctionTool(_make_adk_tool_wrapper(fn, toolkit))
            for fn in toolkit.get_adk_functions()
        ]

        system_prompt = toolkit.intents_as_system_context()
        agent = LlmAgent(
            name="data_assistant",
            model=model,
            instruction=system_prompt,
            tools=adk_tools,
        )

        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name="chatbot",
            user_id=ctx.user_id,
        )

        runner = Runner(
            agent=agent,
            app_name="chatbot",
            session_service=session_service,
        )

        # Build ADK-format message history
        from google.adk.sessions import Session
        from google.genai import types as genai_types

        user_query = messages[-1].content if messages else ""
        history_parts: list[genai_types.Content] = []
        for m in messages[:-1]:
            role = "model" if m.role == "assistant" else "user"
            history_parts.append(
                genai_types.Content(role=role, parts=[genai_types.Part(text=m.content)])
            )

        # Inject ctx into ContextVar so wrapped tools can access it
        token = _agent_ctx_var.set(ctx)
        result = AgentLoopResult()

        try:
            user_content = genai_types.Content(
                role="user", parts=[genai_types.Part(text=user_query)]
            )
            final_response_text = ""

            async for event in runner.run_async(
                user_id=ctx.user_id,
                session_id=session.id,
                new_message=user_content,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = "".join(
                            p.text for p in event.content.parts if p.text
                        )

            # Check for pending clarification set by ask_clarification tool
            if ctx.clarification_state.is_pending(ctx.user_id, ctx.conversation_id):
                result.status = "clarification_pending"
                return result

            result.explanation = final_response_text
            result.status = "completed"

            # Collect sql_used from DataFrameStore metadata is not stored separately;
            # tools record sql in their return dicts. For now we leave sql_used empty —
            # response_formatter fills it from stored frame metadata.

        except Exception as exc:
            logger.error(
                "gemini_agent_loop_error",
                error=str(exc),
                model=model,
                user_id=ctx.user_id,
            )
            result.status = "error"
            result.error = str(exc)
        finally:
            _agent_ctx_var.reset(token)

        return result
