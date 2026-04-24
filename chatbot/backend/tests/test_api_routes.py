"""API route coverage tests — health, auth, conversations, sessions."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def token():
    return create_access_token("test_user_42")


# ── /health ──────────────────────────────────────────────────────────────────


def test_health_returns_200(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_health_body_has_required_keys(client):
    body = client.get("/health").json()
    assert "status" in body
    assert "db" in body
    assert "version" in body
    assert body["status"] == "ok"


def test_health_db_field_is_string(client):
    body = client.get("/health").json()
    assert body["db"] in ("connected", "error")


def test_health_version_non_empty(client):
    body = client.get("/health").json()
    assert body["version"]


# ── /auth/guest ───────────────────────────────────────────────────────────────


def test_guest_login_returns_200(client):
    r = client.post("/auth/guest")
    assert r.status_code == 200


def test_guest_login_returns_token(client):
    body = client.post("/auth/guest").json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user_id"].startswith("guest_")


def test_guest_login_unique_users(client):
    body1 = client.post("/auth/guest").json()
    body2 = client.post("/auth/guest").json()
    assert body1["user_id"] != body2["user_id"]


# ── /auth/token ───────────────────────────────────────────────────────────────


def test_login_returns_200(client):
    r = client.post("/auth/token", json={"username": "alice", "password": "any"})
    assert r.status_code == 200


def test_login_user_id_matches_username(client):
    body = client.post("/auth/token", json={"username": "alice", "password": "any"}).json()
    assert "alice" in body["user_id"]


def test_login_empty_username_returns_400(client):
    r = client.post("/auth/token", json={"username": "", "password": "any"})
    assert r.status_code == 400


# ── /api/conversations ────────────────────────────────────────────────────────


def test_conversations_no_token_returns_422(client):
    r = client.get("/api/conversations")
    assert r.status_code == 422


def test_conversations_invalid_token_returns_401(client):
    r = client.get("/api/conversations?token=not.a.jwt.token")
    assert r.status_code == 401


def test_conversations_valid_token_returns_list(client, token):
    r = client.get(f"/api/conversations?token={token}")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_conversations_empty_for_new_user(client, token):
    r = client.get(f"/api/conversations?token={token}")
    assert r.json() == []


def test_get_messages_unknown_conversation_returns_404(client, token):
    r = client.get(f"/api/conversations/nonexistent-id/messages?token={token}")
    assert r.status_code == 404


def test_delete_conversation_not_found_returns_404(client, token):
    r = client.delete(f"/api/conversations/nonexistent-id?token={token}")
    assert r.status_code == 404


def test_delete_conversation_invalid_token_returns_401(client):
    r = client.delete("/api/conversations/some-id?token=bad")
    assert r.status_code == 401


# ── /api/sessions ─────────────────────────────────────────────────────────────


def test_switch_model_invalid_token_returns_401(client):
    r = client.patch(
        "/api/sessions/conv-1/model?token=bad",
        json={"model": "claude-3-5-sonnet-20241022"},
    )
    assert r.status_code == 401


def test_switch_model_unknown_model_returns_400(client, token):
    r = client.patch(
        f"/api/sessions/conv-1/model?token={token}",
        json={"model": "completely-unknown-model-xyz"},
    )
    assert r.status_code == 400
    assert "Unknown model" in r.json()["detail"]


def test_switch_model_no_token_returns_422(client):
    r = client.patch(
        "/api/sessions/conv-1/model",
        json={"model": "claude-3-5-sonnet-20241022"},
    )
    assert r.status_code == 422


def test_security_create_token_is_valid_jwt(token):
    from app.core.security import decode_token
    user_id = decode_token(token)
    assert user_id == "test_user_42"


def test_security_decode_invalid_returns_none():
    from app.core.security import decode_token
    assert decode_token("garbage") is None


def test_security_decode_empty_returns_none():
    from app.core.security import decode_token
    assert decode_token("") is None
