"""Phase 3 — Session model switch endpoint tests."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return create_access_token("test_user_123")


def test_switch_to_valid_model(client, token):
    """PATCH with a known model returns 200 with model, provider, session_id."""
    resp = client.patch(
        "/api/sessions/conv-abc/model",
        json={"model": "gpt-4o"},
        params={"token": token},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "gpt-4o"
    assert data["provider"] == "openai"
    assert data["session_id"] == "conv-abc"


def test_switch_to_unknown_model_returns_400(client, token):
    """PATCH with an unrecognised model name returns 400."""
    resp = client.patch(
        "/api/sessions/conv-abc/model",
        json={"model": "gpt-99-turbo-ultra"},
        params={"token": token},
    )
    assert resp.status_code == 400
    assert "Unknown model" in resp.json()["detail"]


def test_switch_without_token_returns_401(client):
    """PATCH without a token returns 422 (missing required query param)."""
    resp = client.patch("/api/sessions/conv-abc/model", json={"model": "gpt-4o"})
    assert resp.status_code == 422


def test_switch_with_invalid_token_returns_401(client):
    """PATCH with a bad token returns 401."""
    resp = client.patch(
        "/api/sessions/conv-abc/model",
        json={"model": "gpt-4o"},
        params={"token": "not-a-valid-jwt"},
    )
    assert resp.status_code == 401


def test_switch_anthropic_model(client, token):
    """A Claude model resolves to the anthropic provider."""
    resp = client.patch(
        "/api/sessions/conv-xyz/model",
        json={"model": "claude-sonnet-4-20250514"},
        params={"token": token},
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "anthropic"
