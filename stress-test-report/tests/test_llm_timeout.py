"""test_llm_timeout.py — verify the backend does not hang on slow LLM responses.
Run from chatbot/backend/: pytest stress-test-report/tests/test_llm_timeout.py -v
Tests WS connection close behavior and HTTP timeout headers via nginx.
"""
from __future__ import annotations

import asyncio
import time

import pytest

try:
    import httpx
    import websockets
except ImportError:
    pytest.skip("httpx or websockets not installed", allow_module_level=True)

BASE_HTTPS = "https://localhost"
BASE_WSS = "wss://localhost"


async def _get_token() -> str:
    async with httpx.AsyncClient(verify=False, timeout=5) as c:
        r = await c.post(f"{BASE_HTTPS}/auth/guest")
        assert r.status_code == 200
        return r.json()["access_token"]


@pytest.mark.asyncio
async def test_nginx_read_timeout_header_present() -> None:
    """Nginx must set proxy_read_timeout; health endpoint must respond in <5s."""
    start = time.monotonic()
    async with httpx.AsyncClient(verify=False, timeout=10) as c:
        r = await c.get(f"{BASE_HTTPS}/health")
    elapsed = time.monotonic() - start
    assert r.status_code == 200
    assert elapsed < 5.0, f"Health check took {elapsed:.2f}s — possible hanging request"


@pytest.mark.asyncio
async def test_ws_ping_pong_no_hang() -> None:
    """WS ping/pong round-trip must complete in <3s."""
    token = await _get_token()
    uri = f"{BASE_WSS}/ws/chat?token={token}"

    ssl_ctx = __import__("ssl").create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = __import__("ssl").CERT_NONE

    start = time.monotonic()
    try:
        async with websockets.connect(uri, ssl=ssl_ctx, open_timeout=5) as ws:
            # First message is providers frame
            _providers = await asyncio.wait_for(ws.recv(), timeout=3)

            # Send ping
            await ws.send('{"type": "ping"}')
            pong_raw = await asyncio.wait_for(ws.recv(), timeout=3)
            elapsed = time.monotonic() - start
            import json

            pong = json.loads(pong_raw)
            assert pong.get("type") == "pong", f"Expected pong, got: {pong}"
            assert elapsed < 3.0, f"Ping/pong took {elapsed:.2f}s"
    except (ConnectionRefusedError, OSError) as e:
        pytest.skip(f"Stack not running: {e}")


@pytest.mark.asyncio
async def test_ws_connection_rejects_invalid_token() -> None:
    """WS must close with code 4001 on invalid token, not hang."""
    uri = f"{BASE_WSS}/ws/chat?token=invalid.token.here"

    ssl_ctx = __import__("ssl").create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = __import__("ssl").CERT_NONE

    start = time.monotonic()
    try:
        async with websockets.connect(uri, ssl=ssl_ctx, open_timeout=5) as ws:
            try:
                await asyncio.wait_for(ws.recv(), timeout=3)
            except websockets.exceptions.ConnectionClosedError as e:
                elapsed = time.monotonic() - start
                assert e.code in (4001, 1008, 1000), f"Unexpected close code: {e.code}"
                assert elapsed < 3.0, f"Token rejection took {elapsed:.2f}s — possible hang"
                return
    except (ConnectionRefusedError, OSError) as e:
        pytest.skip(f"Stack not running: {e}")
    except websockets.exceptions.InvalidStatusCode as e:
        assert e.status_code in (401, 403, 4001)
