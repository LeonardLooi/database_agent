# ADK Project Configuration

## 1. pyproject.toml

```toml
[project]
name = "my-adk-service"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "google-adk>=1.28.0",
    "google-genai>=1.0.0",
    "fastapi>=0.135.2",
    "uvicorn[standard]>=0.30.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
strict = true
python_version = "3.14"

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

---

## 2. .env Template

```
GOOGLE_API_KEY=your-gemini-api-key-here
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
APP_NAME=my-adk-service
LOG_LEVEL=INFO
```

Never commit `.env` to version control. Add it to `.gitignore`.

---

### .env File — API Key Loading (Critical)

Google ADK and Gemini SDK do NOT auto-load `.env` files. You MUST explicitly load them.

**Step 1 — Install python-dotenv** (already included in the pyproject.toml template above).

**Step 2 — Load at app startup** (before any ADK/Gemini initialization):

```python
# main.py or app entry point — FIRST lines before any other imports that use env vars
from dotenv import load_dotenv
load_dotenv()  # loads .env from current working directory
```

**Step 3 — .env file format** (in project root, never committed):

```
GOOGLE_API_KEY=your-key-here
# OR
GEMINI_API_KEY=your-key-here
```

**Step 4 — .gitignore** must contain `.env`.

**Verification:** After startup, confirm the key loaded:

```python
import os
assert os.getenv("GOOGLE_API_KEY"), "GOOGLE_API_KEY not loaded — check .env file and load_dotenv() call"
```

❌ Common mistake: placing `load_dotenv()` AFTER importing ADK modules that read env vars at import time. Always call it FIRST.

> **Note:** The pydantic-settings approach in section 3 uses `env_file: ".env"` which also loads `.env`, but only into the `Settings` object — not into `os.environ`. ADK reads directly from `os.environ`, so the explicit `os.environ["GOOGLE_API_KEY"] = settings.google_api_key` export at the end of `config.py` is still required. If you skip pydantic-settings entirely and use `load_dotenv()` alone, ADK can read the key directly from `os.environ` after `load_dotenv()` populates it.

---

## 3. Config Module (pydantic-settings)

```python
# src/config.py
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    google_api_key: str
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    app_name: str = "my-adk-service"
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

# CRITICAL: ADK reads GOOGLE_API_KEY directly from os.environ, NOT from the
# pydantic-settings object. pydantic-settings loads into Settings but does NOT
# automatically populate os.environ. Must explicitly export:
os.environ["GOOGLE_API_KEY"] = settings.google_api_key
```

> **Why this matters:** `google-adk` and `google-genai` call `os.environ["GOOGLE_API_KEY"]` internally. If you only use pydantic-settings without the `os.environ` export, the ADK will raise `"No API key was provided"` even though your `.env` file is correct and `settings.google_api_key` has the value.

Import `settings` wherever config values are needed. For ADK-specific env vars (`GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`), always export them to `os.environ` at startup.

---

## 4. Directory Structure

```
my-adk-service/
+-- src/
|   +-- config.py             # pydantic-settings config
|   +-- main.py               # FastAPI app
|   +-- agents/
|   |   +-- __init__.py
|   |   +-- my_agent.py       # Agent definitions
|   +-- tools/
|   |   +-- __init__.py
|   |   +-- my_tools.py       # Tool functions
|   +-- api/
|   |   +-- __init__.py
|   |   +-- routes.py         # FastAPI routes
+-- tests/
|   +-- test_my_agent.py
+-- pyproject.toml
+-- .env
+-- Dockerfile
+-- docker-compose.yml
```

---

## 5. Dockerfile

Multi-stage build using `uv` for dependency resolution. Final image uses
`python:3.14-slim` with no build tools.

```dockerfile
FROM python:3.14-slim AS builder
WORKDIR /app
RUN pip install uv
COPY pyproject.toml .
RUN uv sync --no-dev

FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /app/.venv .venv
COPY src/ src/
ENV PATH="/app/.venv/bin:$PATH"
ENV GOOGLE_API_KEY=""
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Pass secrets at runtime via environment variables or a secrets manager — never
bake them into the image.

---

## 6. Structured Logging Setup

Use `structlog` for all logging. Never use `print()` or raw `logging.info()`.

```python
import structlog

log = structlog.get_logger()

# In tool functions:
log.info("tool_called", tool_name="my_tool", user_id="u123")
log.error("tool_failed", tool_name="my_tool", error=str(e))

# In API routes:
log.info("request_received", path="/chat", session_id=session_id)
log.error("request_failed", path="/chat", error=str(e))
```

Configure structlog once at application startup in `src/main.py`:

```python
import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
```

---

## 7. Common Commands

```bash
uv run uvicorn src.main:app --reload      # Dev server with hot reload
adk web                                    # ADK built-in web UI (dev only)
uv run pytest -q                          # Run all tests
uv run ruff check --fix .                 # Lint and auto-fix
uv run mypy src/                          # Static type checking
```
