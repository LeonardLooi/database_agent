"""Phase 7 — Integration tests: HTTP endpoints + routing_metadata contract."""
from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.services.llm.base import RoutingDecision, SkillResult


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return create_access_token("integration_user")


# ── routing_metadata contract ─────────────────────────────────────────────────


def test_routing_metadata_shape_call_skill():
    """RoutingDecision enum values are the strings sent over the wire."""
    assert RoutingDecision.CALL_SKILL.value == "CALL_SKILL"
    assert RoutingDecision.CLARIFY.value == "CLARIFY"
    assert RoutingDecision.GENERIC_ANSWER.value == "GENERIC_ANSWER"


def test_skill_result_dataclass_fields():
    """SkillResult carries all fields expected by the done frame serialiser."""
    r = SkillResult(
        output="ok",
        skill_name="test_skill",
        model_used="gpt-4o",
        confidence=0.95,
        routing_decision=RoutingDecision.CALL_SKILL,
        parsed_output={"result": "ok"},
    )
    assert r.output == "ok"
    assert r.confidence == pytest.approx(0.95)
    assert r.parsed_output == {"result": "ok"}


# ── sessions route ─────────────────────────────────────────────────────────────


def test_patch_model_returns_routing_metadata_compatible_provider(client, token):
    """Model switch returns the provider name expected by routing_metadata consumer."""
    resp = client.patch(
        "/api/sessions/test-conv/model",
        json={"model": "gpt-4o"},
        params={"token": token},
    )
    assert resp.status_code == 200
    body = resp.json()
    # The provider name matches what routing_metadata.skill_name consumers expect
    assert body["provider"] == "openai"
    assert body["session_id"] == "test-conv"


def test_patch_unknown_model_400(client, token):
    """Routing metadata is never emitted for an unknown model — 400 returned first."""
    resp = client.patch(
        "/api/sessions/test-conv/model",
        json={"model": "not-a-real-model"},
        params={"token": token},
    )
    assert resp.status_code == 400


# ── health + conversations ─────────────────────────────────────────────────────


def test_health_endpoint(client):
    """Health endpoint must return 200 so Docker healthcheck passes."""
    resp = client.get("/health")
    assert resp.status_code == 200


def test_conversations_requires_auth(client):
    """Conversations list returns 422 (missing token) without a JWT."""
    resp = client.get("/api/conversations")
    assert resp.status_code == 422
