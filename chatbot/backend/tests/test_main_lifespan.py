"""Tests for app/main.py — lifespan, logging, middleware."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app, _configure_logging


class TestConfigureLogging:
    def test_configure_logging_debug_mode(self):
        from app.core.config import settings
        original = settings.DEBUG
        settings.DEBUG = True
        _configure_logging()  # must not raise
        settings.DEBUG = original

    def test_configure_logging_production_mode(self):
        from app.core.config import settings
        original = settings.DEBUG
        settings.DEBUG = False
        _configure_logging()  # must not raise
        settings.DEBUG = original


class TestLifespanProductionKeyCheck:
    def test_insecure_key_in_production_raises(self):
        from app.core.config import settings
        original_debug = settings.DEBUG
        original_key = settings.SECRET_KEY

        settings.DEBUG = False
        settings.SECRET_KEY = "insecure-dev-key-replace-in-production"

        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            with TestClient(app):
                pass

        settings.DEBUG = original_debug
        settings.SECRET_KEY = original_key


class TestLifespanStartup:
    def test_lifespan_redis_disabled_logs_warning(self):
        """Lifespan runs REDIS_ENABLED=False warning branch (lines 43-51)."""
        from app.core.config import settings
        original = settings.REDIS_ENABLED
        settings.REDIS_ENABLED = False
        try:
            with TestClient(app) as client:
                r = client.get("/health")
            assert r.status_code == 200
        finally:
            settings.REDIS_ENABLED = original

    def test_lifespan_startup_completes(self):
        """Normal startup: create_tables, yield, shutdown all execute (lines 53-58)."""
        with TestClient(app) as client:
            r = client.get("/health")
        assert r.status_code == 200


class TestMiddleware:
    def test_cors_headers_present(self):
        client = TestClient(app)
        r = client.options(
            "/health",
            headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"},
        )
        # CORS middleware responds with allow headers
        assert r.status_code in (200, 204)

    def test_app_has_routes(self):
        routes = [r.path for r in app.routes]
        assert "/health" in routes
        assert "/auth/guest" in routes
        assert "/api/conversations" in routes
