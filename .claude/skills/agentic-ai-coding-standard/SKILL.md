---
name: agentic-ai-coding-standard
description: "This skill provides coding standards for Python agentic AI services with LangChain/LangGraph. Use when reviewing or writing Python agentic AI code. Covers state management, tool definitions, graph structure, error handling, and observability."
allowed-tools: Read
metadata:
  triggers: LangChain, LangGraph, agentic AI, Python AI agent, FastAPI agent, state management, tool functions, guardrails, AI agent coding standard
  related-skills: agentic-ai-dev, code-reviewer, security-reviewer
  domain: backend
  role: specialist
  scope: review
  output-format: report
last-reviewed: "2026-03-15"
---

**Iron Law:** Always consult the agentic-ai-dev skill and its MCP sources before writing agent code; never generate LangGraph/LangChain patterns from memory.

# Agentic AI Coding Standards

Mandatory coding standards for all Python agentic AI services using LangChain, LangGraph, and FastAPI.

## Key Rules

| # | Rule | Standard |
|---|------|----------|
| 1 | State typing | Always `TypedDict`; never `dict[str, Any]` |
| 2 | Message lists | `Annotated[list[BaseMessage], add_messages]` |
| 3 | Loop protection | `iteration_count` in state + max check in routing function |
| 4 | Tool functions | `@tool` + docstring + try/except + return strings |
| 5 | LLM instantiation | Factory function; never inline `ChatAnthropic()` in nodes |
| 6 | Temperature | `0` for factual; `0.7` only for creative tasks |
| 7 | Checkpointing | `PostgresSaver` in production; `MemorySaver` only in tests |
| 8 | Error handling | Log + return error state; never swallow exceptions |
| 9 | Naming | `build_<name>_agent()`, `<verb>_node()`, `<Name>State` |
| 10 | Config | pydantic-settings with fail-fast; no `os.getenv()` with silent defaults |
| 11 | Type hints | `mypy --strict`; `Literal` for routing return types |
| 12 | Async | `async def` for all I/O; `ainvoke`/`astream` in API routes |
| 13 | Logging | structlog with `agent_name`, `thread_id`, `node_name` context |
| 14 | Secrets | Never log API keys; redact PII before logging |
| 15 | Testing | Basic invoke + tool usage + iteration limit + error recovery |
| 16 | Cost | Track tokens; configure budget caps; use cheapest viable model |
| 17 | Imports | Group: stdlib → third-party → langchain/langgraph → local |

## Import Ordering

```python
# 1. Standard library
from __future__ import annotations
import json
from typing import Annotated, Literal

# 2. Third-party
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

# 3. LangChain / LangGraph
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

# 4. Local
from ..core.config import settings
from ..core.logging import get_logger
```

## Naming Conventions

| Element | Pattern | Example |
|---------|---------|---------|
| State | `<Name>State` | `AgentState`, `RAGState`, `MultiAgentState` |
| Graph builder | `build_<name>_agent()` | `build_react_agent()`, `build_rag_agent()` |
| Node function | `<verb>_node()` | `agent_node()`, `retrieve_node()`, `grade_node()` |
| Tool function | `<verb>_<noun>()` | `search_web()`, `query_database()`, `calculate_cost()` |
| Provider factory | `LLMProviderFactory` | Singleton, injected via `Depends()` |
| Config | `Settings` | pydantic-settings, singleton `settings` instance |
| Exception | `<Name>Error` | `AgentError`, `ToolError`, `LLMProviderError` |

## File Structure

```
src/<service>/
├── agents/
│   ├── graphs/          # build_*_agent() functions
│   ├── nodes/           # *_node() functions
│   ├── tools/           # @tool functions
│   └── state.py         # TypedDict state schemas
├── rag/                 # RAG-specific code
├── memory/              # Checkpointing + semantic memory
├── guardrails/          # Input/output validation
├── llm/providers.py     # LLM factory
├── core/
│   ├── config.py        # pydantic-settings
│   ├── logging.py       # structlog setup
│   └── exceptions.py    # Exception hierarchy
├── observability/       # Metrics + tracing
├── models/schemas.py    # Pydantic request/response
├── api/routes/          # FastAPI routes
└── main.py              # FastAPI app + lifespan
```

## Reference

For concrete code examples and anti-patterns, Read [reference/agentic-standards-examples.md](reference/agentic-standards-examples.md).

## Error Handling

**Import errors**: Verify LangChain/LangGraph package versions match `pyproject.toml` constraints.

**State type mismatches**: Ensure all graph state fields use `TypedDict` with proper `Annotated` types — never `dict[str, Any]`.

**Graph recursion errors**: Check `recursion_limit` in config and verify `iteration_count` is incremented in routing functions.
