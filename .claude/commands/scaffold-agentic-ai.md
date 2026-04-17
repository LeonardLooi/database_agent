---
description: Scaffold a new Agentic AI service with Python 3.14, LangChain v1.2.8, LangGraph v1.0.7, FastAPI 0.135.2, and production infrastructure
argument-hint: "[project name]"
allowed-tools: Bash, Read, Write, Edit
disable-model-invocation: true
---

# Scaffold Agentic AI Service

**Project name:** $ARGUMENTS (default to "my-agent-service" if not provided)

Delegate to the `agentic-ai-dev` skill for all patterns, templates, and reference files.

## Steps

1. Read the `agentic-ai-dev` skill and its reference files for exact code templates
2. Initialize project — `uv init $ARGUMENTS --python 3.14`
3. Add production + dev dependencies per skill reference `agentic-config-project.md`
4. Create directory structure under `src/<service_name>/` per skill conventions
5. Create core modules (config, logging, exceptions), agent layer (state, tools, nodes, graph), LLM providers, API layer (FastAPI + routes), and tests using skill reference templates
6. Add infrastructure (Dockerfile, docker-compose.dev.yml, .env)
7. Verify — `ruff check src/` and `mypy src/`
