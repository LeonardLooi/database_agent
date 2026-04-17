# Agentic AI Deployment

Docker, docker-compose, production configuration, health checks, and operational patterns.

## Multi-Stage Dockerfile

**File:** `Dockerfile`

```dockerfile
# ============================================
# Stage 1: Builder — install dependencies
# ============================================
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock* ./

# Install production dependencies only
RUN uv sync --no-dev --frozen

# Copy source code
COPY src/ src/

# ============================================
# Stage 2: Runtime — minimal production image
# ============================================
FROM python:3.14-slim AS runtime

# Security: run as non-root user
RUN groupadd -r agent && useradd -r -g agent agent

WORKDIR /app

# Copy virtual environment and source from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

# Set environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"

EXPOSE 8000

# Switch to non-root user
USER agent

# gunicorn + uvicorn workers for production
CMD ["gunicorn", "my_agent_service.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-"]
```

## Docker Compose (Production-like)

**File:** `docker-compose.yml`

```yaml
services:
  # === Application ===
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      - APP_ENV=production
      - LOG_LEVEL=info
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # === PostgreSQL (Checkpointing + Vector Store) ===
  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-agents}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G

  # === Redis (Caching) ===
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 512M

  # === Prometheus (Metrics) ===
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus/alerts.yml:/etc/prometheus/alerts.yml
      - promdata:/prometheus
    depends_on:
      - app

volumes:
  pgdata:
  redisdata:
  promdata:
```

## Prometheus Configuration

**File:** `prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - alerts.yml

scrape_configs:
  - job_name: "agent-service"
    static_configs:
      - targets: ["app:8000"]
    metrics_path: /metrics
    scrape_interval: 10s
```

## Health Checks

**File:** `src/<service>/api/routes/health.py`

```python
from __future__ import annotations

import time

from fastapi import APIRouter, Request

from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Comprehensive health check for all dependencies."""
    checks: dict[str, dict] = {}
    start = time.monotonic()

    # 1. LLM Provider
    try:
        factory = request.app.state.provider_factory
        llm = factory.get_default()
        llm_start = time.monotonic()
        await llm.ainvoke([{"role": "user", "content": "ping"}])
        checks["llm"] = {"status": "healthy", "latency_ms": round((time.monotonic() - llm_start) * 1000)}
    except Exception as e:
        checks["llm"] = {"status": "unhealthy", "error": str(e)[:200]}

    # 2. Checkpoint Database
    try:
        checkpointer = request.app.state.checkpointer
        checks["checkpoint_db"] = {"status": "healthy"}
    except Exception as e:
        checks["checkpoint_db"] = {"status": "unhealthy", "error": str(e)[:200]}

    # 3. Redis (if configured)
    try:
        redis = getattr(request.app.state, "redis", None)
        if redis:
            await redis.ping()
            checks["redis"] = {"status": "healthy"}
        else:
            checks["redis"] = {"status": "not_configured"}
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)[:200]}

    total_latency = round((time.monotonic() - start) * 1000)
    all_healthy = all(
        c.get("status") in ("healthy", "not_configured")
        for c in checks.values()
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": checks,
        "latency_ms": total_latency,
    }


@router.get("/health/ready")
async def readiness_check() -> dict:
    """Lightweight readiness probe for Kubernetes."""
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> dict:
    """Lightweight liveness probe for Kubernetes."""
    return {"status": "alive"}
```

## Graceful Shutdown

```python
import signal
import asyncio

from ..core.logging import get_logger

logger = get_logger(__name__)


async def graceful_shutdown(app):
    """Handle graceful shutdown — drain connections, flush metrics."""
    logger.info("shutdown_initiated")

    # 1. Stop accepting new requests (handled by gunicorn)

    # 2. Wait for in-flight requests to complete (timeout)
    await asyncio.sleep(5)

    # 3. Close checkpointer connection pool
    if hasattr(app.state, "checkpointer"):
        logger.info("closing_checkpointer")
        # Close checkpointer connections

    # 4. Close Redis connection
    if hasattr(app.state, "redis"):
        logger.info("closing_redis")
        await app.state.redis.close()

    # 5. Flush Prometheus metrics
    logger.info("shutdown_complete")
```

## Rate Limiting for LLM Endpoints

```python
from collections import defaultdict
import time


class SimpleRateLimiter:
    """Token bucket rate limiter for LLM endpoints.

    Prevents abuse and controls LLM API costs.
    """

    def __init__(self, requests_per_minute: int = 60):
        self._rpm = requests_per_minute
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        window_start = now - 60.0

        # Clean old entries
        self._buckets[client_id] = [
            t for t in self._buckets[client_id] if t > window_start
        ]

        if len(self._buckets[client_id]) >= self._rpm:
            return False

        self._buckets[client_id].append(now)
        return True
```

## Secret Management

```python
# NEVER do this
# logger.info("Using API key: %s", settings.anthropic_api_key)  # EXPOSED!
# print(f"Key: {api_key}")  # EXPOSED!

# Always do this
logger.info("llm_configured", provider="anthropic", key_prefix=settings.anthropic_api_key[:10] + "...")


# API key rotation pattern
class SecretManager:
    """Manage API key rotation without downtime."""

    def __init__(self, primary_key: str, secondary_key: str = ""):
        self._primary = primary_key
        self._secondary = secondary_key

    def get_active_key(self) -> str:
        return self._primary

    def rotate(self, new_key: str) -> None:
        """Rotate to new key — old key becomes secondary."""
        self._secondary = self._primary
        self._primary = new_key
        logger.info("api_key_rotated", key_prefix=new_key[:10] + "...")
```

## Deployment Checklist

| Check | Command | Expected |
|-------|---------|----------|
| Build | `docker build -t agent-service .` | Exit 0 |
| Health | `curl localhost:8000/api/v1/health` | `{"status": "healthy"}` |
| Metrics | `curl localhost:8000/metrics` | Prometheus format |
| Lint | `ruff check src/` | No errors |
| Types | `mypy src/` | No errors |
| Tests | `pytest -v` | All pass |
| Security | No secrets in code or logs | Verified |
