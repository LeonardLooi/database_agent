# Agentic AI Conventions & Rules

## Package Layout

```
src/<service_name>/
├── agents/
│   ├── graphs/          # StateGraph definitions (build_*_agent functions)
│   ├── nodes/           # Node functions (verb_node pattern)
│   ├── tools/           # @tool definitions
│   └── state.py         # TypedDict state schemas
├── rag/
│   ├── chains/          # RAG chain compositions
│   ├── indexing/        # Document loaders, splitters, indexing
│   └── retrieval/       # Retrievers, rerankers
├── memory/
│   ├── checkpointing.py # PostgresSaver setup
│   └── semantic.py      # Vector store long-term memory
├── guardrails/
│   ├── input.py         # Input validation pipeline
│   └── output.py        # Output validation pipeline
├── llm/
│   └── providers.py     # LLM factory, multi-provider router
├── core/
│   ├── config.py        # pydantic-settings configuration
│   ├── logging.py       # structlog setup
│   └── exceptions.py    # Exception hierarchy
├── observability/
│   ├── metrics.py       # Prometheus metrics
│   └── tracing.py       # LangSmith tracing setup
├── models/
│   └── schemas.py       # Pydantic request/response models
├── api/
│   ├── routes/
│   │   ├── agent.py     # POST /invoke, POST /stream
│   │   └── health.py    # GET /health
│   └── middleware/
│       └── request_context.py  # Correlation ID via contextvars
├── main.py              # FastAPI app with lifespan
└── py.typed             # PEP 561 marker
```

## LangGraph Rules

1. **Always use `TypedDict` for state** — never `dict[str, Any]`
2. **Always use `Annotated[list[BaseMessage], add_messages]`** for message lists — enables proper message merging
3. **Always include `iteration_count: int`** in state — check in routing function to prevent infinite loops
4. **Prefer `Command(goto=...)` pattern** for routing between nodes — cleaner than conditional edges for complex flows
5. **Always set `recursion_limit`** in config (default: 25) — safety net for runaway graphs
6. **Use `PostgresSaver` in production** — `MemorySaver` is for tests only; it's not persistent
7. **Always pass `thread_id` in config** — `{"configurable": {"thread_id": "..."}}`; required for checkpointing

## FastAPI Integration Rules

1. **All endpoints are `async def`** — never block the event loop
2. **Use `Depends()` for agent graph injection** — configure in lifespan, inject via dependency
3. **Use `StreamingResponse` with `text/event-stream`** — for streaming agent responses
4. **Include `/api/v1/health`** — ping LLM providers, DB, vector store
5. **Propagate `thread_id`** from request to graph config — enables conversation continuity

## LangGraph Agent Implementation Checklist

Pre-ship checklist for LangGraph agents. Run through before marking any agent implementation complete.

```
□ LLM initialized with pinned model version
  □ Anthropic: "claude-sonnet-4-5" (or confirm current stable with MCP)
  □ Google: "gemini-3.1-flash-exp" (see adk-gemini-prompt-templates.md)
  □ OpenAI: confirm version from Context7 docs

□ Embeddings configured (if RAG)
  □ Model pinned (e.g., voyage-3-large, text-embedding-3-large)
  □ Dimension matches pgvector schema (see pgvector-schema-reviewer agent)

□ Tools implemented correctly
  □ Every @tool has: docstring, Pydantic input schema, try/except, structured error return
  □ Async tools use ainvoke, not invoke

□ Memory system chosen and implemented
  □ Short-term: PostgresSaver (prod) or MemorySaver (test only)
  □ Long-term: Vector store semantic search (if needed)
  □ thread_id propagated from request → graph config

□ Iteration limit in state (REQUIRED — Iron Law)
  □ iteration_count: int = 0 in TypedDict state
  □ Routing function checks limit before continuing

□ LangSmith tracing enabled
  □ LANGCHAIN_TRACING_V2=true in .env
  □ LANGCHAIN_PROJECT set to service name

□ Streaming implemented (if user-facing)
  □ astream() used instead of ainvoke
  □ FastAPI StreamingResponse with text/event-stream

□ Health checks configured
  □ GET /api/v1/health pings LLM provider, DB, vector store
  □ Returns 200 only when all dependencies healthy

□ Caching layer (if needed for cost optimization)
  □ Redis cache for repeated identical queries
  □ Cache TTL appropriate for content freshness requirements

□ Retry logic configured
  □ tenacity @retry on LLM calls with exponential backoff
  □ Max retries: 3; wait: 4s–10s

□ Evaluation tests written
  □ At least 1 test per tool (isolation test)
  □ At least 1 end-to-end agent routing test
  □ LangSmith eval dataset created for quality tracking

□ API endpoints documented
  □ POST /invoke and POST /stream with request/response schemas
  □ thread_id handling documented (new vs. resuming conversation)
```

## Prompt Selection Quick Reference

When writing prompts for agents, choose the template based on the LLM provider:

| Provider | Model | Prompt structure | Reference |
|----------|-------|-----------------|-----------|
| Anthropic (LangChain) | claude-sonnet-4-5 | XML tags: `<context>`, `<task>`, `<thinking>` | `agentic-prompt-engineering.md` |
| Google (ADK) | gemini-3.1-flash-exp | Markdown `**bold**` + numbered steps | `adk-gemini-prompt-templates.md` |
| OpenAI (LangChain) | gpt-4o / gpt-5 | `##SECTION##` delimiters + JSON output block | `agentic-prompt-optimization.md` |

For advanced techniques (Constitutional AI, Tree-of-Thoughts, canary rollout, prompt versioning):
→ LangGraph agents: `agentic-prompt-optimization.md`
→ ADK agents: `adk-gemini-prompt-templates.md`
