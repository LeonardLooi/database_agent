from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

import structlog

from app.core.config import settings
from app.core.exceptions import AuthConfigError
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import AgentLoopResult, BaseLLMProvider

if TYPE_CHECKING:
    from app.agent.skill_registry import SkillSchema
    from app.agent.tools.query_tools import AgentToolContext
    from app.services.llm.base import SkillResult

logger = structlog.get_logger()

_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

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
        self._credentials = self._resolve_credentials()
        import google.generativeai as genai

        genai.configure(credentials=self._credentials)
        self._genai = genai

    @classmethod
    def is_available(cls) -> bool:
        # ADC is always potentially available; fail fast at instantiation if not.
        return True

    # ── auth ──────────────────────────────────────────────────────────────────

    def _resolve_credentials(self) -> Any:
        """Resolve GCP credentials using a 3-priority ADC chain.

        Priority 1 — Impersonation (production preferred):
            Set GCP_IMPERSONATE_SA=shared-sa@project.iam.gserviceaccount.com.
            Source credentials come from ambient ADC; the call impersonates the
            shared service account.  Requires roles/iam.serviceAccountTokenCreator
            on the caller identity.

        Priority 2 — Key file (local dev fallback):
            Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json.
            Uses the service account key directly.

        Priority 3 — Ambient ADC (last resort):
            Uses whatever google.auth.default() resolves.  Logs a WARNING
            because the identity may not be the intended shared SA.

        Returns:
            A google.auth.credentials.Credentials instance (auto-refreshable).

        Raises:
            AuthConfigError: if all three paths fail, with actionable remediation.
        """
        try:
            import google.auth
            import google.auth.exceptions
            import google.auth.impersonated_credentials
            import google.auth.transport.requests
            import google.oauth2.service_account
        except ImportError as exc:
            raise AuthConfigError(
                "google-auth is not installed. Add google-auth>=2.23.0 to requirements.txt."
            ) from exc

        # Priority 1 — Impersonation
        if settings.GCP_IMPERSONATE_SA:
            logger.info(
                "gcp_auth_path",
                path="impersonation",
                target_principal=settings.GCP_IMPERSONATE_SA,
            )
            try:
                source_creds, _ = google.auth.default(scopes=_SCOPES)
                return google.auth.impersonated_credentials.Credentials(
                    source_credentials=source_creds,
                    target_principal=settings.GCP_IMPERSONATE_SA,
                    target_scopes=_SCOPES,
                )
            except google.auth.exceptions.DefaultCredentialsError as exc:
                raise AuthConfigError(
                    f"GCP impersonation failed: source credentials not found.\n"
                    f"Target SA: {settings.GCP_IMPERSONATE_SA}\n"
                    f"Remediation: run 'gcloud auth application-default login' or "
                    f"ensure the execution environment provides ambient ADC."
                ) from exc

        # Priority 2 — Key file
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            logger.info(
                "gcp_auth_path",
                path="key_file",
                file=settings.GOOGLE_APPLICATION_CREDENTIALS,
            )
            try:
                return google.oauth2.service_account.Credentials.from_service_account_file(
                    settings.GOOGLE_APPLICATION_CREDENTIALS,
                    scopes=_SCOPES,
                )
            except (FileNotFoundError, ValueError) as exc:
                raise AuthConfigError(
                    f"GCP key-file auth failed: {exc}\n"
                    f"File: {settings.GOOGLE_APPLICATION_CREDENTIALS}\n"
                    f"Remediation: verify the file path and that it is a valid "
                    f"service account JSON key."
                ) from exc

        # Priority 3 — Ambient ADC
        logger.warning(
            "gcp_auth_ambient_adc",
            message=(
                "Shared SA not explicitly targeted. Verify ADC identity. "
                "Set GCP_IMPERSONATE_SA or GOOGLE_APPLICATION_CREDENTIALS for production."
            ),
        )
        try:
            creds, _ = google.auth.default(scopes=_SCOPES)
            return creds
        except google.auth.exceptions.DefaultCredentialsError as exc:
            raise AuthConfigError(
                "GCP auth failed: no credentials found via any path.\n"
                "Remediation options:\n"
                "  Production:   set GCP_IMPERSONATE_SA=shared-sa@project.iam.gserviceaccount.com\n"
                "  Local (key):  set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json\n"
                "  Local (ADC):  run 'gcloud auth application-default login'"
            ) from exc

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

        # Refresh credentials so the ADK runner picks up a valid token.
        # google.auth.transport.requests.Request refreshes synchronously;
        # we run it in a thread to avoid blocking the event loop.
        import google.auth.transport.requests

        def _refresh() -> None:
            self._credentials.refresh(google.auth.transport.requests.Request())

        await asyncio.get_event_loop().run_in_executor(None, _refresh)

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

        from google.genai import types as genai_types

        user_query = messages[-1].content if messages else ""

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

            if ctx.clarification_state.is_pending(ctx.user_id, ctx.conversation_id):
                result.status = "clarification_pending"
                return result

            result.explanation = final_response_text
            result.status = "completed"

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

    # ── skill execution ───────────────────────────────────────────────────────

    async def execute_skill(
        self,
        session_id: str,
        user_message: str,
        skill: "SkillSchema",
        params: dict,
        model: str,
    ) -> "SkillResult":
        import json

        from app.agent.skill_prompt_builder import SkillPromptBuilder
        from app.services.llm.base import RoutingDecision, SkillResult

        system_prompt = SkillPromptBuilder.build(skill, params)
        try:
            gen_model = self._genai.GenerativeModel(
                model_name=model,
                system_instruction=system_prompt,
            )
            response = await gen_model.generate_content_async(user_message)
            output = response.text
        except Exception as exc:
            logger.error("gemini_execute_skill_error", error=str(exc), skill=skill.name)
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
