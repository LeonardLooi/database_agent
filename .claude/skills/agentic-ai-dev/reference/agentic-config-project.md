# Agentic AI Project Configuration

## pyproject.toml

**File:** `pyproject.toml`

```toml
[project]
name = "my-agent-service"
version = "0.1.0"
description = "Production AI agent service"
requires-python = ">=3.14"
dependencies = [
    # LangChain / LangGraph
    "langchain-core>=1.2.8",
    "langchain-anthropic>=1.3.0",
    "langchain-openai>=1.1.0",
    "langgraph>=1.0.7",
    "langgraph-checkpoint-postgres>=3.0.0",

    # API
    "fastapi>=0.135.2",
    "uvicorn[standard]>=0.32.0",
    "gunicorn>=23.0.0",

    # Data validation
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",

    # Observability
    "langsmith>=0.2.0",
    "prometheus-client>=0.21.0",
    "structlog>=24.4.0",

    # HTTP / DB
    "httpx>=0.28.0",
    "asyncpg>=0.30.0",

    # Vector stores (pick one)
    # "langchain-chroma>=0.2.0",
    # "langchain-pinecone>=0.2.0",
    # "langchain-pgvector>=0.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
    "mypy>=1.13.0",
]

[tool.ruff]
target-version = "py314"
line-length = 120
src = ["src"]

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
    "SIM", # flake8-simplify
    "TCH", # flake8-type-checking
    "RUF", # ruff-specific
]
ignore = ["E501"]  # line length handled by formatter

[tool.ruff.lint.isort]
known-first-party = ["my_agent_service"]
section-order = ["future", "standard-library", "third-party", "first-party", "local-folder"]

[tool.mypy]
python_version = "3.14"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[[tool.mypy.overrides]]
module = ["langchain.*", "langgraph.*", "langsmith.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Environment Configuration

**File:** `.env.example`

```bash
# === LLM Providers ===
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=...

# === LangSmith Observability ===
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=my-agent-service
LANGSMITH_TRACING=true

# === Database ===
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/agents
CHECKPOINT_DB_URI=postgresql://postgres:postgres@localhost:5432/agents

# === Vector Store ===
# CHROMA_HOST=localhost
# CHROMA_PORT=8000
# PINECONE_API_KEY=...

# === Redis (optional caching) ===
REDIS_URL=redis://localhost:6379/0

# === Application ===
APP_NAME=my-agent-service
APP_ENV=development
LOG_LEVEL=info
DEFAULT_MODEL=claude-sonnet-4-20250514
DEFAULT_TEMPERATURE=0
MAX_ITERATIONS=25
TOKEN_BUDGET=4096
```

## Configuration Module

**File:** `src/<service>/core/config.py`

```python
from __future__ import annotations

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with fail-fast validation.

    All required fields MUST be set via environment variables or .env file.
    Missing values cause immediate startup failure — no silent defaults for secrets.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- LLM Providers ---
    anthropic_api_key: str
    openai_api_key: str = ""
    google_api_key: str = ""

    # --- LangSmith ---
    langsmith_api_key: str = ""
    langsmith_project: str = "my-agent-service"
    langsmith_tracing: bool = True

    # --- Database ---
    database_url: str
    checkpoint_db_uri: str

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Application ---
    app_name: str = "my-agent-service"
    app_env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["debug", "info", "warning", "error"] = "info"
    default_model: str = "claude-sonnet-4-20250514"
    default_temperature: float = 0.0
    max_iterations: int = 25
    token_budget: int = 4096

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_anthropic_key(cls, v: str) -> str:
        if not v or not v.startswith("sk-ant-"):
            raise ValueError("ANTHROPIC_API_KEY must be set and start with 'sk-ant-'")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or "://" not in v:
            raise ValueError("DATABASE_URL must be a valid connection string")
        return v

    @field_validator("checkpoint_db_uri")
    @classmethod
    def validate_checkpoint_uri(cls, v: str) -> str:
        if not v or "://" not in v:
            raise ValueError("CHECKPOINT_DB_URI must be a valid connection string")
        return v


# Singleton — import this everywhere
settings = Settings()  # type: ignore[call-arg]
```

## Structured Logging

**File:** `src/<service>/core/logging.py`

```python
from __future__ import annotations

import logging
import sys

import structlog

from .config import settings


def setup_logging() -> None:
    """Configure structlog with JSON output and correlation ID support."""

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.app_env == "development":
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())

    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger with correlation ID support."""
    return structlog.get_logger(name)
```

## Exception Hierarchy

**File:** `src/<service>/core/exceptions.py`

```python
from __future__ import annotations


class AgentServiceError(Exception):
    """Base exception for all agent service errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class AgentError(AgentServiceError):
    """Error during agent graph execution."""


class ToolError(AgentServiceError):
    """Error during tool execution."""


class LLMProviderError(AgentServiceError):
    """Error from LLM provider (rate limit, auth, timeout)."""


class GuardrailError(AgentServiceError):
    """Input or output failed guardrail validation."""


class RAGError(AgentServiceError):
    """Error during RAG retrieval or indexing."""


class MemoryError(AgentServiceError):
    """Error accessing memory store."""


class ConfigurationError(AgentServiceError):
    """Missing or invalid configuration."""
```

## Docker Configuration

**File:** `Dockerfile`

```dockerfile
# --- Build stage ---
FROM python:3.14-slim AS builder

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen

COPY src/ src/

# --- Runtime stage ---
FROM python:3.14-slim AS runtime

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Use gunicorn with uvicorn workers for production
CMD ["gunicorn", "my_agent_service.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
```

**File:** `docker-compose.dev.yml`

```yaml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: agents
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```
