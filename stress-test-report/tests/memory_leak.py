"""memory_leak.py — heap growth test for FastAPI backend.
Run from chatbot/backend/: pytest stress-test-report/tests/memory_leak.py -v
Requires httpx, pytest-asyncio, and the backend running locally on :8080 or via HTTPS.
"""
from __future__ import annotations

import asyncio
import tracemalloc

import pytest

try:
    import httpx
except ImportError:
    pytest.skip("httpx not installed", allow_module_level=True)

BASE_URL = "https://localhost"
ITERATIONS = 200
MAX_HEAP_GROWTH_MB = 50.0


@pytest.mark.asyncio
async def test_no_memory_leak_on_health_calls() -> None:
    """200 repeated health calls should not grow heap by more than 50MB."""
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        tasks = [client.get(f"{BASE_URL}/health") for _ in range(ITERATIONS)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    ok_count = sum(
        1 for r in responses if isinstance(r, httpx.Response) and r.status_code == 200
    )
    assert ok_count > ITERATIONS * 0.95, f"Too many failures: {ok_count}/{ITERATIONS} succeeded"

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_growth_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
    total_growth_mb = total_growth_bytes / (1024 * 1024)

    assert total_growth_mb < MAX_HEAP_GROWTH_MB, (
        f"Heap grew by {total_growth_mb:.2f}MB over {ITERATIONS} calls — "
        f"possible memory leak (threshold: {MAX_HEAP_GROWTH_MB}MB)"
    )


@pytest.mark.asyncio
async def test_no_memory_leak_on_auth_calls() -> None:
    """200 guest token requests should not grow heap by more than 50MB."""
    tracemalloc.start()
    snapshot_before = tracemalloc.take_snapshot()

    async with httpx.AsyncClient(verify=False, timeout=10) as client:
        responses = []
        for _ in range(ITERATIONS):
            r = await client.post(f"{BASE_URL}/auth/guest")
            responses.append(r)

    ok_count = sum(1 for r in responses if r.status_code == 200)
    assert ok_count > ITERATIONS * 0.95, f"Too many auth failures: {ok_count}/{ITERATIONS}"

    snapshot_after = tracemalloc.take_snapshot()
    tracemalloc.stop()

    stats = snapshot_after.compare_to(snapshot_before, "lineno")
    total_growth_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
    total_growth_mb = total_growth_bytes / (1024 * 1024)

    assert total_growth_mb < MAX_HEAP_GROWTH_MB, (
        f"Heap grew by {total_growth_mb:.2f}MB over {ITERATIONS} auth calls "
        f"(threshold: {MAX_HEAP_GROWTH_MB}MB)"
    )
