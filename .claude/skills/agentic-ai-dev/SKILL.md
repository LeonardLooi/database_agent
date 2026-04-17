---
name: agentic-ai-dev
description: "This skill provides patterns and templates for building production AI agents with Python 3.14, LangChain v1.2.8, LangGraph v1.0.7, and FastAPI 0.135.2. Use when creating AI agents, RAG systems, graph workflows, tools, memory systems, or agent tests."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: AI agent, LangChain, LangGraph, RAG system, graph workflow, FastAPI, Python 3.14, LangGraph agent, memory system, agent test
  related-skills: agentic-ai-coding-standard, python-dev, mcp-builder
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NO AGENT GRAPH WITHOUT AN ITERATION LIMIT AND A HUMAN-IN-THE-LOOP CHECKPOINT — unbounded loops and silent runaway agents are production incidents**

# Agentic AI Development Skill — Python 3.14 + LangChain + LangGraph + FastAPI

## Quick Scaffold

```bash
uv init my-agent-service && cd my-agent-service
uv add "langchain-core>=1.2.8" "langchain-anthropic>=1.3.0" "langchain-openai>=1.1.0" "langgraph>=1.0.7" \
  "fastapi>=0.135.2" "uvicorn[standard]" pydantic pydantic-settings \
  langsmith prometheus-client structlog httpx asyncpg \
  "langgraph-checkpoint-postgres>=3.0.0"
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

## Process

1. **Scaffold** — `uv init` + install dependencies
2. **Configure** — `core/config.py` with pydantic-settings, `.env`, structured logging
3. **Define State** — `TypedDict` with `Annotated[list, add_messages]` for each agent
4. **Build Graph** — `StateGraph` with typed nodes, conditional edges, checkpointing
5. **Define Tools** — `@tool` with docstrings, Pydantic input schemas, error handling
6. **Add Memory** — Checkpointing (PostgresSaver), semantic memory (vector store)
7. **Add Guardrails** — Input validation, prompt injection detection, output validation
8. **Expose API** — FastAPI routes for invoke/stream with `thread_id` propagation
9. **Write Tests** — Basic invoke, tool usage, iteration limit, error recovery, RAG quality
10. **Deploy** — Docker multi-stage, gunicorn + uvicorn, health checks, Prometheus

## Key Patterns

| Pattern | Implementation | Reference |
|---------|---------------|-----------|
| Agent Graphs | `StateGraph` + typed nodes + conditional edges | `agentic-templates-basic.md` |
| Tools | `@tool` + docstring + Pydantic input + try/except | `agentic-templates-tools.md` |
| LLM Binding | Factory function per provider, `.bind_tools()` | `agentic-llm-routing.md` |
| Routing | `Command(goto=...)` pattern (LangGraph) | `agentic-templates-advanced.md` |
| Checkpointing | `PostgresSaver` (prod) / `MemorySaver` (test) | `agentic-memory-systems.md` |
| Streaming | `astream()` + `stream_mode` + FastAPI SSE | `agentic-streaming-hitl.md` |
| Human-in-the-Loop | `interrupt_before` + approval node | `agentic-streaming-hitl.md` |
| RAG | Embeddings → Vector Store → Retriever → Reranker | `agentic-templates-rag.md` |
| Guardrails | 12-layer pipeline: input → process → output | `agentic-guardrails-security.md` |
| Structured Output | `.with_structured_output(PydanticModel)` | `agentic-prompt-engineering.md` |
| Error Recovery | Retry node + fallback model + graceful degradation | `agentic-templates-resilience.md` |
| Config | pydantic-settings + fail-fast validators | `agentic-config-project.md` |
| Caching | 4-tier Q1→Q2→Q3→L3 with backfill; @cached_tool decorator | `agentic-caching-patterns.md` |

## Conventions & Rules

> For package layout, LangGraph rules, and FastAPI integration rules, read `reference/agentic-conventions.md`

## Documentation Sources

Before generating code, consult these sources for current syntax and APIs:

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| LangGraph | `https://langchain-ai.github.io/langgraph/llms-full.txt` | StateGraph, nodes, edges, checkpointing APIs |
| Pydantic v2 | `https://docs.pydantic.dev/latest/llms-full.txt` | Model validation, settings, Field constraints |
| FastAPI / LangChain | `Context7` MCP | Latest LangChain tools, FastAPI patterns |

## Reference Files

| File | Content | When to Use |
|------|---------|-------------|
| `agentic-config-project.md` | pyproject.toml, .env, config, Docker, ruff/mypy | Project setup |
| `agentic-templates-core.md` | FastAPI app, main.py, routes, middleware, base state | Creating API layer |
| `agentic-templates-basic.md` | ReAct Agent, Multi-Agent Collaborative patterns | Building basic agents |
| `agentic-templates-advanced.md` | Hierarchical Supervisor, Command, Sub-Graph patterns | Building complex agents |
| `agentic-templates-resilience.md` | Error Recovery Agent, key design decisions | Agent error handling |
| `agentic-templates-rag.md` | 6 RAG architectures + document ingestion pipeline | Building RAG systems |
| `agentic-templates-tools.md` | @tool patterns, MCP integration, retry/timeout | Defining agent tools |
| `agentic-guardrails-security.md` | 12-layer security framework | Adding safety layers |
| `agentic-memory-systems.md` | 7-layer memory hierarchy, practical implementations | Adding memory to agents |
| `agentic-streaming-hitl.md` | Streaming + Human-in-the-Loop patterns | Real-time responses, approval flows |
| `agentic-llm-routing.md` | Multi-provider routing, cost calculation, fallback chains | Multi-model setups |
| `agentic-observability.md` | LangSmith, Prometheus, structured logging | Monitoring and debugging |
| `agentic-testing.md` | Agent testing patterns, mocks, fixtures | Writing agent tests |
| `agentic-deployment.md` | Docker, docker-compose, production config | Deploying agents |
| `agentic-debugging.md` | Debugging playbook, common issues | Troubleshooting agents |
| `agentic-cost-optimization.md` | Cost management, budget caps, prompt optimization | Reducing LLM costs |
| `agentic-prompt-engineering.md` | Advanced prompting, structured output, templates | Writing better prompts |
| `agentic-error-handling.md` | Agent, tool, LLM provider, and API error handling patterns | Error handling in agents |
| `agentic-review-checklist.md` | Agentic AI review checklist (used by `agentic-ai-reviewer` agent) | Code reviews |
| `agentic-prompt-optimization.md` | Constitutional AI, Tree-of-Thoughts, model-specific templates (Claude/Gemini/GPT), prompt versioning registry, canary rollout, LLM-as-judge | Optimizing prompt quality; multi-model deployments; production prompt lifecycle |
| `llm-judge-advanced.md` | Production LLM-as-Judge: bias taxonomy (position, length, self-enhancement), position swap protocol, rubric generation, PoLL ensemble, hierarchical eval | Evaluating agent outputs with reliability; high-stakes eval decisions |
| `agentic-caching-patterns.md` | 4-tier cache (Q1 LRU→Q2 Redis→Q3 semantic→L3 Anthropic), backfill, @cached_tool decorator, cache key generation, Prometheus metrics | Adding caching to LangGraph agents |
| `agentic-makefile-patterns.md` | 40+ Makefile commands for setup, testing, RAG, memory, evaluation, Docker, observability — reference patterns for agentic AI services | Setting up developer workflow automation |

## Common Commands

```bash
uvicorn src.main:app --reload                          # Run dev server (hot reload)
pytest -q                                              # Run tests (quiet output)
pytest -q --cov=src --cov-report=term-missing          # Tests with coverage
ruff check --fix .                                     # Lint and auto-fix
ruff format .                                          # Format code
mypy src/                                              # Type check
```

## Error Handling

> For error handling patterns and code examples, read `reference/agentic-error-handling.md`

**LLM provider errors**: Use retry with exponential backoff + fallback model chain. Never let provider errors crash the graph.

**Tool execution errors**: Wrap all `@tool` functions in try/except. Return structured error messages the LLM can reason about.

**Graph infinite loops**: Always include `iteration_count` in state and check it in the routing function.

## Post-Code Review

After writing agentic AI code, dispatch these reviewer agents:
- `agentic-ai-reviewer` — graph correctness, guardrails, iteration limits, cost efficiency
- `security-reviewer` — tool input validation, prompt injection defense
