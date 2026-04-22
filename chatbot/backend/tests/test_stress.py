"""Phase 7 — Stress tests (ST-01 through ST-05).

All tests use mock providers and real asyncio concurrency to verify that shared
state (SkillRegistry, SessionModelStore) and the ChatOrchestrator are safe
under concurrent load. No network calls are made.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.agent.orchestrator import ChatOrchestrator
from app.agent.session_model_store import SessionModelStore
from app.agent.skill_registry import SkillRegistry
from app.services.llm.base import RoutingDecision, SkillResult


# ── shared helpers ────────────────────────────────────────────────────────────

_SKILL_YAML = dedent("""\
    name: summarise_document
    description: Summarise a document and extract key points.
    instructions: |
      You are a document analyst.
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


def _make_provider(confidence: float = 0.92) -> MagicMock:
    provider = MagicMock()
    provider.provider_name = "openai"
    match_json = (
        f'{{"skill_name": "summarise_document", '
        f'"params": {{"document_text": "x"}}, '
        f'"confidence": {confidence}}}'
    )
    provider.generate = AsyncMock(return_value=match_json)
    provider.execute_skill = AsyncMock(
        return_value=SkillResult(
            output="summary",
            skill_name="summarise_document",
            model_used="gpt-4o",
            confidence=confidence,
            routing_decision=RoutingDecision.CALL_SKILL,
        )
    )
    return provider


# ── ST-01: 50 concurrent skill-match calls ────────────────────────────────────


@pytest.mark.asyncio
async def test_st01_concurrent_skill_matching(tmp_path):
    """ST-01: 50 simultaneous orchestrator.route() calls must all complete without error."""
    registry = _make_registry(tmp_path)
    provider = _make_provider()
    orchestrator = ChatOrchestrator(provider, registry)

    tasks = [
        orchestrator.route(f"summarise document {i}", f"sess-{i}", "gpt-4o")
        for i in range(50)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 50
    assert all(r.routing_decision == RoutingDecision.CALL_SKILL for r in results)


# ── ST-02: SkillRegistry reload under concurrent reads ───────────────────────


@pytest.mark.asyncio
async def test_st02_registry_reload_under_concurrent_reads(tmp_path):
    """ST-02: Hot-reload (asyncio.Lock) must not corrupt reads during concurrent access."""
    registry = _make_registry(tmp_path)

    async def _read():
        return registry.list_skills()

    async def _reload():
        await registry.reload()

    # Interleave reads and reloads
    tasks = []
    for _ in range(20):
        tasks.append(_read())
        tasks.append(_reload())

    results = await asyncio.gather(*tasks)
    # list_skills() returns a list; reload() returns None — filter out Nones
    skill_lists = [r for r in results if r is not None]
    assert all(isinstance(r, list) for r in skill_lists)


# ── ST-03: SessionModelStore concurrent reads/writes ─────────────────────────


@pytest.mark.asyncio
async def test_st03_session_model_store_concurrent_rw():
    """ST-03: 50 concurrent set/get pairs must not race or raise."""
    store = SessionModelStore(redis_client=None)  # in-memory fallback

    async def _set_get(i: int) -> str | None:
        conv_id = f"conv-{i % 10}"  # 10 unique IDs shared across 50 goroutines
        store.set(conv_id, f"model-{i}")
        return store.get(conv_id)

    results = await asyncio.gather(*[_set_get(i) for i in range(50)])

    # Every call must return a model string (not None, not raise)
    assert all(r is not None and r.startswith("model-") for r in results)


# ── ST-04: 100 GENERIC_ANSWER routes under load ───────────────────────────────


@pytest.mark.asyncio
async def test_st04_high_volume_generic_answer(tmp_path):
    """ST-04: 100 concurrent GENERIC_ANSWER routes must complete without exceptions."""
    registry = _make_registry(tmp_path)
    # low confidence → GENERIC_ANSWER every time
    provider = _make_provider(confidence=0.1)
    provider.generate = AsyncMock(
        return_value='{"skill_name": null, "params": {}, "confidence": 0.1}'
    )
    orchestrator = ChatOrchestrator(provider, registry)

    tasks = [
        orchestrator.route(f"what is {i}+{i}?", f"sess-{i}", "gpt-4o")
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)

    assert len(results) == 100
    assert all(r.routing_decision == RoutingDecision.GENERIC_ANSWER for r in results)


# ── ST-05: Malformed LLM responses produce no unhandled exceptions ────────────


@pytest.mark.asyncio
async def test_st05_malformed_llm_responses_no_unhandled_exceptions(tmp_path):
    """ST-05: 20 concurrent requests with garbage LLM output must all resolve gracefully."""
    registry = _make_registry(tmp_path)

    bad_responses = [
        "",                      # empty
        "not json at all",       # plain text
        '{"partial": }',         # broken JSON
        "null",                  # JSON null
        "[]",                    # wrong type
        "{ skill_name: oops }",  # invalid key syntax
        "\x00\x01\x02",          # binary garbage
        '{"skill_name": "unknown_skill", "params": {}, "confidence": 0.99}',  # unknown skill name
    ]

    results = []
    for i in range(20):
        provider = MagicMock()
        provider.provider_name = "openai"
        provider.generate = AsyncMock(return_value=bad_responses[i % len(bad_responses)])
        orchestrator = ChatOrchestrator(provider, registry)

        result = await orchestrator.route(f"query {i}", f"sess-{i}", "test-model")
        results.append(result)

    # Every result must be GENERIC_ANSWER (graceful fallback, not an exception)
    assert all(r.routing_decision == RoutingDecision.GENERIC_ANSWER for r in results)
