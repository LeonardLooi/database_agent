"""Phase 2 — ChatOrchestrator unit tests."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agent.orchestrator import ChatOrchestrator
from app.agent.skill_registry import SkillRegistry
from app.services.llm.base import RoutingDecision, SkillResult


# ── fixtures ──────────────────────────────────────────────────────────────────

_SKILL_YAML = dedent("""\
    name: summarise_document
    description: Summarise a document and extract key points.
    instructions: |
      You are a document analyst. Extract key points.
    parameters:
      document_text:
        type: string
        required: true
    output_format: |
      {"summary": "..."}
    tags: [document]
""")


def _make_registry(tmp_path: Path) -> SkillRegistry:
    (tmp_path / "summarise_document.yaml").write_text(_SKILL_YAML)
    with patch.object(SkillRegistry, "_start_watcher"):
        return SkillRegistry(tmp_path)


def _make_provider(generate_return: str = "") -> MagicMock:
    provider = MagicMock()
    provider.generate = AsyncMock(return_value=generate_return)
    provider.execute_skill = AsyncMock(
        return_value=SkillResult(
            output="summary output",
            skill_name="summarise_document",
            model_used="test-model",
            confidence=1.0,
            routing_decision=RoutingDecision.CALL_SKILL,
        )
    )
    return provider


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_call_skill_when_high_confidence(tmp_path):
    """Confidence >= 0.85 routes to CALL_SKILL and returns SkillResult."""
    registry = _make_registry(tmp_path)
    match_json = '{"skill_name": "summarise_document", "params": {"document_text": "hello"}, "confidence": 0.92}'
    provider = _make_provider(match_json)

    orchestrator = ChatOrchestrator(provider, registry)
    result = await orchestrator.route("summarise this document", "sess-1", "test-model")

    assert result.routing_decision == RoutingDecision.CALL_SKILL
    assert result.skill_result is not None
    assert result.matched_skill_name == "summarise_document"


@pytest.mark.asyncio
async def test_clarify_when_medium_confidence(tmp_path):
    """Confidence in [0.50, 0.85) routes to CLARIFY with a question."""
    registry = _make_registry(tmp_path)
    match_json = '{"skill_name": "summarise_document", "params": {}, "confidence": 0.65}'
    provider = _make_provider(match_json)

    orchestrator = ChatOrchestrator(provider, registry)
    result = await orchestrator.route("process this thing", "sess-1", "test-model")

    assert result.routing_decision == RoutingDecision.CLARIFY
    assert result.clarification_message is not None
    assert "summarise" in result.clarification_message.lower() or "document" in result.clarification_message.lower()


@pytest.mark.asyncio
async def test_generic_answer_when_no_skill_matches(tmp_path):
    """Confidence < 0.50 (or null skill) routes to GENERIC_ANSWER."""
    registry = _make_registry(tmp_path)
    match_json = '{"skill_name": null, "params": {}, "confidence": 0.1}'
    provider = _make_provider(match_json)

    orchestrator = ChatOrchestrator(provider, registry)
    result = await orchestrator.route("what is the weather?", "sess-1", "test-model")

    assert result.routing_decision == RoutingDecision.GENERIC_ANSWER


@pytest.mark.asyncio
async def test_generic_answer_when_no_skills_loaded(tmp_path):
    """When the registry is empty, always routes GENERIC_ANSWER without calling LLM."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with patch.object(SkillRegistry, "_start_watcher"):
        registry = SkillRegistry(empty_dir)

    provider = _make_provider()
    orchestrator = ChatOrchestrator(provider, registry)
    result = await orchestrator.route("anything at all", "sess-1", "test-model")

    assert result.routing_decision == RoutingDecision.GENERIC_ANSWER
    provider.generate.assert_not_called()


@pytest.mark.asyncio
async def test_generic_answer_on_malformed_llm_response(tmp_path):
    """A non-JSON response from skill-match falls back to GENERIC_ANSWER gracefully."""
    registry = _make_registry(tmp_path)
    provider = _make_provider("I cannot decide!")  # not JSON

    orchestrator = ChatOrchestrator(provider, registry)
    result = await orchestrator.route("what is 2+2?", "sess-1", "test-model")

    assert result.routing_decision == RoutingDecision.GENERIC_ANSWER
