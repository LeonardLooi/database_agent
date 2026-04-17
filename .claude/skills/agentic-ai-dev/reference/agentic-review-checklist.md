# Agentic AI Code Review Checklist

## Issue Severity

| Level | Criteria | Action |
|-------|----------|--------|
| P0 — Critical | Security vulnerability, data loss risk, infinite loop, production crash | BLOCK merge |
| P1 — High | Missing error handling, no tests, cost risk, observability gap | REQUEST CHANGES |
| P2 — Medium | Naming violation, missing docs, suboptimal pattern | REQUEST CHANGES |
| P3 — Low | Style preference, minor optimization | COMMENT only |

## Review Areas

### P0 — Critical

**1. Graph Correctness**
- State uses `TypedDict` (not `dict[str, Any]`)
- Message lists use `Annotated[list[BaseMessage], add_messages]`
- `iteration_count` exists in state AND is checked in routing function
- `recursion_limit` is set in graph config
- No circular edges without exit condition
- Checkpointer is configured (not `None` in production code)
- `thread_id` is propagated from request to graph config

**2. Safety / Guardrails**
- User input is sanitized before passing to LLM
- Prompt injection detection is present for user-facing agents
- PII is redacted before logging
- Output is validated before returning to user
- Hallucination check exists for RAG agents
- Token budget is enforced per request
- User input is NEVER placed in system prompt strings

**3. Tool Validation**
- Every `@tool` has a descriptive docstring (LLMs need this)
- Every tool has try/except that returns error strings
- Tools return `str` (not dict, list, or other types)
- No destructive operations without HITL approval gate
- No stack traces leaked to users via tool error messages
- Tool inputs are validated (Pydantic `args_schema` for complex inputs)

**4. Error Handling**
- Error counter in state + fallback node when budget exhausted
- Provider fallback chain configured (primary → secondary → fast)
- Structured error responses in API (no raw exception messages)
- No empty `except: pass` blocks
- No silent empty returns on error (e.g., `return []`)

**5. Secret Management**
- No hardcoded API keys in source code
- API keys not logged (even at debug level)
- No PII in LangSmith trace metadata
- `.env` file in `.gitignore`
- Secrets loaded via pydantic-settings with validation

### P1 — High

**6. Cost Management**
- Model selection matches task complexity (not using opus for classification)
- Prompt caching is used for long system prompts (Anthropic `cache_control`)
- Context is managed (trimming/summarization for long conversations)
- Token usage is tracked via Prometheus metrics
- Budget caps are configured (per-request, per-session, daily)

**7. Testing**
- Basic invoke test exists (agent responds to simple message)
- Tool usage test exists (agent uses tool when appropriate)
- Iteration limit test exists (agent stops at max iterations)
- Error recovery test exists (agent handles LLM/tool errors)
- RAG tests exist if RAG is implemented (retrieval quality, groundedness)
- All tests use `MemorySaver` — none connect to real databases
- Test coverage >= 80% for agent graphs, >= 90% for guardrails

**8. Observability**
- LangSmith tracing is configured
- Structured logging with correlation IDs (structlog + contextvars)
- Prometheus metrics for latency, token usage, errors, cost
- Health check endpoint pings all dependencies

### P2 — Medium

**9. Architecture**
- Clean separation: routes → graphs → tools → services
- LLM instantiation via factory function (not inline)
- Configuration via pydantic-settings (not `os.getenv()`)
- All I/O operations are `async def`
- Import order: stdlib → third-party → langchain → local

**10. Documentation**
- Agent purpose documented (what it does, when to use it)
- Tool docstrings explain when and how to use each tool
- Complex routing logic has comments explaining the decision
- State fields have docstring/comment explaining their purpose

## Output Format

For each issue found:

```
### [P{level}] {area}: {short description}

**File:** `{file_path}:{line_number}`
**Issue:** {what's wrong}
**Fix:** {specific code change or approach}
```

## Summary Template

```
## Review Summary

**Verdict:** {APPROVE | REQUEST CHANGES | BLOCK}

### Statistics
- Files reviewed: {count}
- P0 issues: {count}
- P1 issues: {count}
- P2 issues: {count}
- P3 issues: {count}

### Critical Issues
{list P0 issues}

### Required Changes
{list P1 issues}

### Suggestions
{list P2/P3 issues}
```

## Reference

Consult the `agentic-ai-dev` skill reference files for expected patterns:
- `agentic-templates-basic.md` — ReAct, Multi-Agent patterns
- `agentic-templates-advanced.md` — Supervisor, Command, Sub-Graph patterns
- `agentic-templates-resilience.md` — Error Recovery, design decisions
- `agentic-templates-tools.md` — Tool patterns
- `agentic-guardrails-security.md` — Security patterns
- `agentic-testing.md` — Test patterns
- `agentic-observability.md` — Observability patterns
- `agentic-standards-examples.md` — Anti-pattern reference
