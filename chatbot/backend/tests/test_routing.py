"""Phase 4 — Confidence extraction tests for routing.py."""
from __future__ import annotations

import pytest

from app.agent.routing import (
    enhance_anthropic,
    enhance_gemini,
    enhance_openai,
    extract_confidence,
)


def test_gemini_uses_self_reported_confidence_when_nonzero():
    result = {"skill_name": "summarise_document", "params": {}, "confidence": 0.92}
    assert enhance_gemini(result, "please summarise this doc", "summarise a document") == pytest.approx(0.92)


def test_gemini_falls_back_to_keyword_heuristic_when_zero():
    result = {"skill_name": "summarise_document", "params": {}, "confidence": 0.0}
    score = enhance_gemini(result, "summarise document", "summarise a document for me")
    assert 0.0 < score <= 0.49  # heuristic returns a value but caps at 0.49


def test_gemini_heuristic_returns_zero_for_no_overlap():
    result = {"confidence": 0.0}
    score = enhance_gemini(result, "what is the weather", "summarise a document")
    assert score == pytest.approx(0.0)


def test_openai_returns_self_reported():
    result = {"confidence": 0.75}
    assert enhance_openai(result) == pytest.approx(0.75)


def test_extract_confidence_dispatches_by_provider():
    result = {"confidence": 0.88}
    assert extract_confidence("gemini", result) == pytest.approx(0.88)
    assert extract_confidence("openai", result) == pytest.approx(0.88)
    assert extract_confidence("anthropic", result) == pytest.approx(0.88)
    assert extract_confidence("aws", result) == pytest.approx(0.88)
