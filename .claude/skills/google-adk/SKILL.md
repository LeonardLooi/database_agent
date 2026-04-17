---
name: google-adk
description: "Google ADK (Agent Development Kit) Python skill. Use when building AI agents with google-adk, Gemini models, SequentialAgent, ParallelAgent, LoopAgent, FunctionTool, McpToolset, session management, memory services, artifact storage, callbacks, or FastAPI integration for ADK agents."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: google-adk, ADK, gemini agent, SequentialAgent, ParallelAgent, LoopAgent, FunctionTool, McpToolset, google genai, adk agent, vertex ai agent
  related-skills: python-dev, agentic-ai-dev, mcp-builder
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

# Google ADK Development Skill — Python + Gemini + FastAPI

## Iron Law

**NEVER call the real Gemini API in unit tests.** Always use `InMemoryRunner` for tests. Production agents use `Runner` with real session services. Mixing these means real API costs, flaky tests, and non-deterministic CI.

## Quick Scaffold (Two Options)

### Option A: agent-starter-pack (Recommended for production)

```bash
uvx agent-starter-pack create my-agent --agent adk --prototype --agent-guidance-filename CLAUDE.md -y
# Templates: adk (default), adk_a2a (A2A protocol), agentic_rag (RAG)
```

Generates project with Terraform, Dockerfile, CI/CD, eval harness. Use `enhance` to add deployment later.

### Option B: Manual setup (Simpler, no deployment scaffold)

```bash
uv init my-adk-service && cd my-adk-service
uv add google-adk "google-genai>=1.0.0" "fastapi>=0.135.2" "uvicorn[standard]" pydantic pydantic-settings structlog
uv add --dev pytest pytest-asyncio httpx ruff mypy
```

## Process

0. **Write DESIGN_SPEC.md** — Before any code, write a spec covering: purpose, example use cases, required tools, safety constraints, success criteria, edge cases. Save as `DESIGN_SPEC.md` in the project root. This is your contract — all implementation must align with it.
1. **Scaffold** — `uv init` + install `google-adk` + `google-genai`; confirm `uv add "google-adk>=1.28.0"` resolves without error
2. **Configure** — `.env` with `GOOGLE_API_KEY` / `GOOGLE_CLOUD_PROJECT`; load via `pydantic-settings` `BaseSettings`; never hardcode keys
3. **Define Agent** — `Agent(name, model, instruction, tools)` using `model="gemini-3.1-flash"`; write docstrings on every tool function
4. **Compose Agents** — use `SequentialAgent`, `ParallelAgent`, or `LoopAgent` for multi-step workflows; set `output_key` on each sub-agent that passes state downstream
5. **Define Tools** — plain Python functions with type hints and docstrings; use `pydantic.BaseModel` for complex inputs; accept `tool_context: ToolContext` to read/write session state
6. **Add Callbacks** — `before_model_callback`, `after_model_callback`, `before_tool_callback`, `after_tool_callback`, `on_model_error_callback`, `on_tool_error_callback` for rate limiting, logging, and structured error handling
7. **Session Management** — `InMemorySessionService()` for dev/test; `VertexAiSessionService(project_id, location)` for production; always call `create_session` before first `runner.run`
8. **Add Memory** — `InMemoryMemoryService` for dev; pass `memory_service` to `Runner`; add `load_memory` built-in tool to agents that need long-term recall
9. **Expose API** — FastAPI routes using `runner.run_async()` with `StreamingResponse` for SSE; one `Runner` instance per app lifecycle
10. **Write Tests** — `InMemoryRunner` for unit tests; `pytest-asyncio` for async tests; test tools in isolation, then agent routing end-to-end
11. **Deploy** — Docker + `uvicorn`; inject `GOOGLE_API_KEY` as env var; use `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` for Vertex AI session service in prod

## Key Patterns

| Pattern | Implementation | Reference |
|---------|---------------|-----------|
| Single Agent | `Agent(name, model, instruction, tools)` | `adk-core-patterns.md` |
| Sequential Pipeline | `SequentialAgent(sub_agents=[a, b, c])` + `output_key` per agent | `adk-agent-types.md` |
| Parallel Analysis | `ParallelAgent(sub_agents=[...])` + `output_key` per agent | `adk-agent-types.md` |
| Iterative Refinement | `LoopAgent(sub_agents=[...], max_iterations=N)` + `exit_loop` | `adk-agent-types.md` |
| Agent Handoff | `transfer_to_agent` built-in + `sub_agents=[...]` on root | `adk-agent-handoff.md` |
| Custom Tools | Plain function with docstring + `ToolContext` for state | `adk-tools-basic.md` |
| MCP Integration | `McpToolset(connection_params=StdioConnectionParams(...))` | `adk-tools-basic.md` |
| Structured Output | `output_schema=PydanticModel` + `output_key="key"` | `adk-core-patterns.md` |
| Callbacks | `before_model_callback`, `after_model_callback`, `before_tool_callback` | `adk-tools-callbacks.md` |
| Session State | `tool_context.state["key"]` read/write | `adk-core-patterns.md` |
| Memory | `InMemoryMemoryService` + `load_memory` tool | `adk-memory-artifacts.md` |
| Testing | `InMemoryRunner` + pytest-asyncio | `adk-testing.md` |
| FastAPI SSE | `runner.run_async()` + `StreamingResponse` | `adk-fastapi-integration.md` |
| Evaluation | `adk eval` + evalset schema + LLM-as-judge | See Google ADK docs |
| Deployment | Agent Engine, Cloud Run, CI/CD | See Google ADK docs |
| Observability | Cloud Trace, prompt logging, agent analytics | See Google ADK docs |

## Code Preservation Rules

- **NEVER change the model** in existing code unless explicitly asked — changing `gemini-3.1-flash` to another model is a breaking change
- **NEVER rewrite working agent code** — if the agent works, refactor incrementally
- **NEVER remove tools** from an agent without explicit approval — tools are part of the agent's contract
- **NEVER rename output_key values** — downstream agents reference them by name

## Documentation Sources

| Source | URL / Tool | Purpose |
|--------|-----------|---------|
| Google ADK Python | `https://context7.com/google/adk-python/llms.txt` | Official ADK API reference |
| Google GenAI types | Context7 MCP — resolve `google-genai` | `types.Part`, `types.Content`, `GenerateContentConfig` |
| Pydantic v2 | Context7 MCP — resolve `pydantic` | `BaseModel`, `Field`, validators |
| ADK Docs MCP | `adk-docs` MCP server (installed) | Live ADK documentation |

## Reference Files

| File | Contents |
|------|----------|
| `reference/adk-core-patterns.md` | Agent config, Runner patterns (sync/async), App class, session management |
| `reference/adk-structured-output.md` | Session state access, structured output schemas, UserContent construction |
| `reference/adk-agent-types.md` | SequentialAgent, ParallelAgent, LoopAgent, composition patterns |
| `reference/adk-agent-handoff.md` | Agent handoff via transfer_to_agent, output_key state passing rules |
| `reference/adk-tools-basic.md` | FunctionTool, ToolContext, async tools, Pydantic inputs, McpToolset (all 4 connection modes) |
| `reference/adk-tools-callbacks.md` | Callbacks: before/after model, on_model_error, before/after tool, on_tool_error |
| `reference/adk-memory-artifacts.md` | Memory services, load_memory tool, artifact storage, semantic search |
| `reference/adk-fastapi-integration.md` | FastAPI + StreamingResponse SSE, lifespan runner setup, request/response models |
| `reference/adk-testing.md` | InMemoryRunner unit tests, pytest-asyncio patterns, tool isolation, agent routing |
| `reference/adk-project-config.md` | pyproject.toml, .env setup, directory structure, Dockerfile, logging, commands |
| `reference/adk-gemini-prompt-templates.md` | Gemini-specific `LlmAgent` instruction templates — base structure, RAG with citations, constitutional AI (2-agent SequentialAgent), Tree-of-Thoughts, multi-step analysis, model selection guide (Flash vs Pro) |

## Common Commands

```bash
# Run dev server via ADK web UI
adk web

# Run FastAPI app with uvicorn
uvicorn src.main:app --reload --port 8000

# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy src/

# Lint + format
uv run ruff check src/ && uv run ruff format src/

# Install all deps from lockfile
uv sync
```

## Error Handling

ADK-specific error handling rules:

- **Provider errors** — wrap `runner.run()` / `runner.run_async()` in try/except; catch `google.api_core.exceptions.GoogleAPICallError`; log with full context (user_id, session_id, model); rethrow or return structured error response — never swallow
- **Tool errors** — use `on_tool_error_callback` to intercept and log; return a descriptive error string from tools (ADK surfaces it to the model); never return empty string or `None` silently
- **Loop limits** — `LoopAgent` stops at `max_iterations`; ensure `exit_loop` is called by the agent's instruction before the limit; log when loop exits by limit vs. by tool call
- **Callback abort** — returning a non-None value from `before_model_callback` skips the model call; document this explicitly in the callback with a comment
- **Session not found** — always call `session_service.get_session()` before `runner.run()`; if `None`, call `create_session()` first

All error paths must:
1. Log with structured logger (structlog) including `user_id`, `session_id`, `agent_name`
2. Either rethrow or return an error state — no silent empty returns
3. Surface the failure to the user (API error response, SSE error event)

## Post-Code Review

After implementing any ADK agent feature:

1. Dispatch `agentic-ai-reviewer` agent — pass the agent graph structure and tool implementations
2. Dispatch `security-reviewer` — flag any tool that calls external APIs or handles user PII
3. Confirm: no hardcoded API keys, all inputs validated, all error paths logged
