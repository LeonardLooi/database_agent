"""Extended API route tests — conversations delete, get_messages, health error."""
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
    return create_access_token("test_extended_user")


# ── Conversations: create then delete ────────────────────────────────────────

class TestDeleteConversation:
    def _create_conv(self, client, token, conv_id="conv-del-test-1"):
        """Use WS connect to create a conversation indirectly, or hit the route directly."""
        # Conversations are created via WS — instead, test the 404 path
        return conv_id

    def test_delete_nonexistent_returns_404(self, client, token):
        r = client.delete(f"/api/conversations/nonexistent-xyz?token={token}")
        assert r.status_code == 404

    def test_delete_wrong_user_returns_404(self, client):
        other_token = create_access_token("other_user_99")
        r = client.delete(f"/api/conversations/some-conv?token={other_token}")
        assert r.status_code == 404

    def test_delete_invalid_token_returns_401(self, client):
        r = client.delete("/api/conversations/some-conv?token=invalid")
        assert r.status_code == 401


# ── Conversations: messages ────────────────────────────────────────────────

class TestGetMessages:
    def test_get_messages_nonexistent_conv_returns_404(self, client, token):
        r = client.get(f"/api/conversations/nonexistent-abc/messages?token={token}")
        assert r.status_code == 404

    def test_get_messages_wrong_user_returns_404(self, client):
        other_token = create_access_token("other_user_88")
        r = client.get(f"/api/conversations/some-conv/messages?token={other_token}")
        assert r.status_code == 404

    def test_get_messages_invalid_token_returns_401(self, client):
        r = client.get("/api/conversations/some-conv/messages?token=bad")
        assert r.status_code == 401


# ── Health error path ─────────────────────────────────────────────────────

class TestHealthError:
    def test_health_db_error_still_returns_200(self, client):
        from unittest.mock import patch, AsyncMock
        from sqlalchemy.ext.asyncio import AsyncSession

        async def _fail_execute(*args, **kwargs):
            raise RuntimeError("DB connection refused")

        with patch.object(AsyncSession, "execute", side_effect=_fail_execute):
            r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["db"] == "error"


# ── Sessions: model switch creates entry ─────────────────────────────────

class TestSessionsModelSwitch:
    def test_switch_gemini_model(self, client, token):
        r = client.patch(
            "/api/sessions/conv-gemini/model",
            json={"model": "gemini-2.0-flash"},
            params={"token": token},
        )
        assert r.status_code == 200
        assert r.json()["provider"] == "gemini"

    def test_switch_bedrock_model(self, client, token):
        r = client.patch(
            "/api/sessions/conv-aws/model",
            json={"model": "amazon.nova-pro-v1:0"},
            params={"token": token},
        )
        assert r.status_code == 200
        assert r.json()["provider"] == "aws"
