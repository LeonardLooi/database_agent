from __future__ import annotations

import json
import re
from dataclasses import dataclass

import structlog

from app.agent.query_router import QueryRouter
from app.agent.routing import extract_confidence
from app.agent.skill_registry import SkillRegistry
from app.schemas.ws_messages import MsgIn
from app.services.llm.base import BaseLLMProvider, RoutingDecision, SkillResult

logger = structlog.get_logger()

# Skill-match prompt: asks the active provider to identify the best skill
_SKILL_MATCH_PROMPT = """\
You are a routing assistant. Your only job is to match the user message to one of the \
available skills below, or return null if none match.

Available skills:
{skill_descriptions}

User message: {user_message}

Respond with ONLY valid JSON in this exact format (no extra text, no markdown):
{{"skill_name": "<name or null>", "params": {{}}, "confidence": 0.0}}

Rules:
- skill_name must be exactly one of the skill names listed above, or the JSON value null
- confidence is a float 0.0–1.0 (your certainty that this skill fits the request)
- params must contain extracted parameter values for the matched skill (empty dict if null)
"""

_HIGH_CONFIDENCE = 0.85
_MIN_CONFIDENCE = 0.50


@dataclass
class OrchestratorResult:
    """Unified result from ChatOrchestrator.route().

    routing_decision tells the caller what to do next:
    - CALL_SKILL:      skill_result is populated — return it to the user
    - CLARIFY:         clarification_message is set — ask the user this question
    - GENERIC_ANSWER:  no skill matched — use_agent_loop tells the caller whether to
                       run the database agent loop (True) or stream freeform chat (False)
    """

    routing_decision: RoutingDecision
    skill_result: SkillResult | None = None
    clarification_message: str | None = None
    confidence: float = 0.0
    matched_skill_name: str | None = None
    use_agent_loop: bool = False
    intent_hint: str = ""


class ChatOrchestrator:
    """Routes user messages to YAML skills, then falls back to database agent or chat.

    Step 1 — Skill match: ask the active provider which skill (if any) matches.
    Step 2 — Confidence routing: apply CALL_SKILL / CLARIFY / GENERIC_ANSWER thresholds.
    Step 3 — Execution: on CALL_SKILL, run execute_skill() and return SkillResult.
              On GENERIC_ANSWER, delegate the is_data_query / intent-estimation logic
              that previously lived in chat_ws.py (via the internal QueryRouter).

    QueryRouter is intentionally an implementation detail of this class — external code
    routes all messages through ChatOrchestrator only (R2 resolution).
    """

    def __init__(self, provider: BaseLLMProvider, registry: SkillRegistry) -> None:
        self._provider = provider
        self._registry = registry
        self._query_router = QueryRouter()

    async def route(
        self,
        user_message: str,
        session_id: str,
        model: str,
    ) -> OrchestratorResult:
        # Skip skill matching entirely if no skills are loaded
        if self._registry.list_skills():
            match_result = await self._match_skill(
                user_message, self._registry.get_all_descriptions(), model
            )
            skill_name: str | None = match_result.get("skill_name")
            params: dict = match_result.get("params") or {}
            skill_desc = ""
            if skill_name:
                _s = self._registry.get_skill(skill_name)
                skill_desc = _s.description if _s else ""
            confidence = extract_confidence(
                self._provider.provider_name, match_result, user_message, skill_desc
            )

            logger.info(
                "orchestrator_route",
                skill_name=skill_name,
                confidence=confidence,
                session_id=session_id,
            )

            if skill_name and confidence >= _HIGH_CONFIDENCE:
                skill = self._registry.get_skill(skill_name)
                if skill:
                    try:
                        skill_result = await self._provider.execute_skill(
                            session_id=session_id,
                            user_message=user_message,
                            skill=skill,
                            params=params,
                            model=model,
                        )
                    except NotImplementedError:
                        logger.warning(
                            "execute_skill_not_implemented",
                            provider=type(self._provider).__name__,
                        )
                    else:
                        return OrchestratorResult(
                            routing_decision=RoutingDecision.CALL_SKILL,
                            skill_result=skill_result,
                            confidence=confidence,
                            matched_skill_name=skill_name,
                        )

            elif skill_name and _MIN_CONFIDENCE <= confidence < _HIGH_CONFIDENCE:
                skill = self._registry.get_skill(skill_name)
                desc = skill.description.strip() if skill else skill_name
                return OrchestratorResult(
                    routing_decision=RoutingDecision.CLARIFY,
                    clarification_message=(
                        f"I want to make sure I help correctly. Did you mean: {desc}?"
                    ),
                    confidence=confidence,
                    matched_skill_name=skill_name,
                )

        # GENERIC_ANSWER — delegate to existing QueryRouter logic
        return self._generic_answer(user_message)

    def _generic_answer(self, user_message: str) -> OrchestratorResult:
        use_agent_loop = bool(
            user_message and self._query_router.is_data_query(user_message)
        )
        intent_hint = ""

        if not use_agent_loop:
            all_intents = self._query_router._loader.all_intents()
            if all_intents:
                suggestions = "\n".join(
                    f"  • {i.name}: {i.description}" for i in all_intents
                )
                intent_hint = f"\n\n---\n*Available data topics I can query:*\n{suggestions}"

        return OrchestratorResult(
            routing_decision=RoutingDecision.GENERIC_ANSWER,
            use_agent_loop=use_agent_loop,
            intent_hint=intent_hint,
        )

    def estimate_intent(self, user_message: str):
        """Delegate intent estimation to the internal QueryRouter."""
        return self._query_router.estimate_intent(user_message)

    def get_intent(self, name: str):
        """Delegate intent lookup to the internal QueryRouter loader."""
        return self._query_router._loader.get(name)

    async def _match_skill(
        self, user_message: str, descriptions: str, model: str
    ) -> dict:
        prompt = _SKILL_MATCH_PROMPT.format(
            skill_descriptions=descriptions,
            user_message=user_message,
        )
        try:
            raw = await self._provider.generate(
                messages=[MsgIn(role="user", content=prompt)],
                model=model,
                max_tokens=256,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as exc:
            logger.warning("skill_match_failed", error=str(exc))
        return {"skill_name": None, "params": {}, "confidence": 0.0}
