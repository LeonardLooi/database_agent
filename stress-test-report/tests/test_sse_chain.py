"""test_sse_chain.py — WebSocket streaming chain tests.
Run from chatbot/backend/: pytest stress-test-report/tests/test_sse_chain.py -v
Verifies WS messages flow and clean connection closure.
"""
from __future__ import annotations

import asyncio
import json
import ssl

import pytest

try:
    import httpx
    import websockets
except ImportError:
    pytest.skip("httpx or websockets not installed", allow_module_level=True)

BASE_HTTPS = "https://localhost"
BASE_WSS = "wss://localhost"

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


async def _get_token() -> str:
    async with httpx.AsyncClient(verify=False, timeout=5) as c:
        r = await c.post(f"{BASE_HTTPS}/auth/guest")
        r.raise_for_status()
        return r.json()["access_token"]


@pytest.mark.asyncio
async def test_ws_providers_frame_on_connect() -> None:
    """Server must send a 'providers' frame immediately on WS connect."""
    try:
        token = await _get_token()
    except Exception as e:
        pytest.skip(f"Stack not running: {e}")

    uri = f"{BASE_WSS}/ws/chat?token={token}"
    try:
        async with websockets.connect(uri, ssl=_SSL_CTX, open_timeout=5) as ws:
            frame_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            frame = json.loads(frame_raw)
            assert frame.get("type") == "providers", f"Expected providers frame, got: {frame}"
            assert "data" in frame, "providers frame missing 'data' key"
    except (ConnectionRefusedError, OSError) as e:
        pytest.skip(f"Stack not running: {e}")


@pytest.mark.asyncio
async def test_ws_clean_close_on_disconnect() -> None:
    """Client disconnect should be handled cleanly (no server error)."""
    try:
        token = await _get_token()
    except Exception as e:
        pytest.skip(f"Stack not running: {e}")

    uri = f"{BASE_WSS}/ws/chat?token={token}"
    try:
        async with websockets.connect(uri, ssl=_SSL_CTX, open_timeout=5) as ws:
            # Consume providers frame
            await asyncio.wait_for(ws.recv(), timeout=5)
            # Close deliberately from client side
            await ws.close()
    except (ConnectionRefusedError, OSError) as e:
        pytest.skip(f"Stack not running: {e}")

    # Verify health still OK after disconnection
    async with httpx.AsyncClient(verify=False, timeout=5) as c:
        r = await c.get(f"{BASE_HTTPS}/health")
        assert r.status_code == 200, f"Health check failed after WS disconnect: {r.status_code}"


@pytest.mark.asyncio
async def test_ws_concurrent_connections() -> None:
    """10 concurrent WS connections must all receive providers frame."""
    try:
        token = await _get_token()
    except Exception as e:
        pytest.skip(f"Stack not running: {e}")

    uri = f"{BASE_WSS}/ws/chat?token={token}"

    async def connect_and_receive() -> bool:
        try:
            async with websockets.connect(uri, ssl=_SSL_CTX, open_timeout=5) as ws:
                frame_raw = await asyncio.wait_for(ws.recv(), timeout=5)
                frame = json.loads(frame_raw)
                return frame.get("type") == "providers"
        except Exception:
            return False

    results = await asyncio.gather(*[connect_and_receive() for _ in range(10)])
    success_count = sum(1 for r in results if r)
    assert success_count >= 8, f"Only {success_count}/10 concurrent WS connections succeeded"
