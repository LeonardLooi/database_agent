---
description: Scaffold a new Python 3.14 FastAPI project with Pydantic, async SQLAlchemy, and proper structure
argument-hint: "[project name]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Scaffold Python FastAPI Service

Create a new Python 3.14 / FastAPI project with the following:

**Project name:** $ARGUMENTS (default to "my-python-api" if not provided)

## Steps
1. **Create `.gitignore` first** — before any other file. Include: `__pycache__/`, `.env`, `*.pem`, `*.key`, `.venv/`, `dist/`, `*.egg-info/`, `.DS_Store`, `.mypy_cache/`, `.ruff_cache/`
2. Initialize project with `pyproject.toml` (dependencies + dev dependencies, include `pip-audit` in dev deps)
3. Set up virtual environment with `uv init` or `python -m venv`
3. Create folder structure: `src/<package>/api/routes/`, `models/`, `services/`, `repositories/`, `core/`, `utils/`
4. Create `main.py` with FastAPI app, lifespan handler, and router includes
5. Create `core/config.py` with pydantic-settings
6. Create a sample Pydantic model (request + response)
7. Create a sample route handler, service, and repository
8. Add a health check endpoint at `GET /api/v1/health`
9. Create `tests/conftest.py` with async test client fixture
10. Add a pytest test for the sample endpoint
11. Configure ruff (linting) and mypy (type checking) in pyproject.toml
12. Create a `Dockerfile` for production
13. Add a `.env.example` file
14. Run `pip audit` — fix or document any critical/high CVEs before proceeding
15. Print summary of created files and next steps

Use the python-dev skill for patterns and templates.
