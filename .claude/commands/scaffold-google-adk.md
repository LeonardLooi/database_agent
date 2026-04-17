---
description: Scaffold a new Google ADK service with Gemini, FastAPI, sessions, memory, and production infrastructure
argument-hint: "[project name]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Scaffold Google ADK Service

**Project name:** $ARGUMENTS (default to "my-adk-service" if not provided)

Delegate to the `google-adk` skill for all patterns, templates, and reference files.

## Steps

1. Read the `google-adk` skill (`SKILL.md` and reference files) before generating any code
2. **Ask the user which setup approach they want:**

   > "Do you want:
   > **A) agent-starter-pack** (production-grade — includes Terraform, Dockerfile, CI/CD, eval harness; recommended for real projects)
   > **B) Manual setup** (simpler, no deployment scaffold — use for learning or quick prototypes)"

3. Proceed based on their answer:

   ### Option A: agent-starter-pack

   ```bash
   uvx agent-starter-pack create $ARGUMENTS --agent adk --prototype --agent-guidance-filename CLAUDE.md -y
   ```

   - Templates: `adk` (default), `adk_a2a` (A2A protocol), `agentic_rag` (RAG with data ingestion)
   - Project name must be ≤26 characters, lowercase, letters/numbers/hyphens only
   - Do NOT `mkdir` the project directory first — the CLI creates it
   - After scaffolding, write `DESIGN_SPEC.md` in the project root
   - Run `make playground` (or `adk web .`) for interactive testing
   - To add deployment later: `uvx agent-starter-pack enhance . --deployment-target agent_engine -y`

   ### Option B: Manual setup

   Initialize project — `uv init $ARGUMENTS --python 3.14`

   Add dependencies:
   ```bash
   uv add google-adk "google-genai>=1.0.0" "fastapi>=0.135.2" "uvicorn[standard]" pydantic pydantic-settings structlog
   uv add --dev pytest pytest-asyncio httpx ruff mypy
   ```

   Create directory structure per `adk-project-config.md`:
   - `src/config.py` — pydantic-settings with GOOGLE_API_KEY
   - `src/agents/` — Agent definitions using gemini-3.1-flash
   - `src/tools/` — Tool functions with full docstrings
   - `src/api/routes.py` — /chat and /stream endpoints
   - `src/main.py` — FastAPI app with lifespan + Runner init

   Create a sample agent demonstrating: Agent with 1 tool, InMemorySessionService, POST /chat endpoint, GET /stream SSE endpoint

   Create tests in `tests/test_agent.py` using InMemoryRunner (no real API calls)

   Create `.env` from template in `adk-project-config.md`

   Create `Dockerfile` per `adk-project-config.md`

4. Verify:
   - `uv run ruff check src/` (Option B) or `make lint` (Option A)
   - `uv run mypy src/` (Option B only)
   - `uv run pytest -q` (tests must not call real Gemini API)
5. Report scaffolded files with paths as evidence
