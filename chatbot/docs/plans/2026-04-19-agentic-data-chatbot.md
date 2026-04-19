# Plan: Agentic Data Chatbot — Multi-Provider Orchestration

**Date:** 2026-04-19
**Status:** APPROVED — awaiting implementation start
**Mode:** Big Change

---

## Approved Direction

Build a production-grade agentic data chatbot on top of the existing `/chatbot` project.
Each LLM provider (Anthropic, OpenAI, Gemini/ADK, AWS Bedrock) acts as its own orchestrator —
using its native agent loop to match YAML intents, invoke shared DB connector tools, combine
DataFrames, and generate a structured response (NL explanation + CSV + formatted table + SQL/Python code).

---

## Architecture

```
Angular 21 Chat UI (unchanged)
        │ WebSocket /ws/chat
chat_ws.py (extended)
        │
  QueryRouter: is_data_query() → freeform → existing stream() path
                               → data query → provider.run_agent_loop()
        │
  ┌─────┴──────────────────────────────────────┐
  │  Each provider = orchestrator              │
  │  Anthropic  → tool_use multi-turn loop     │
  │  OpenAI     → function_calling loop        │
  │  gemini_provider.py → ADK (LlmAgent /      │
  │               ParallelAgent/SequentialAgent)│
  │  AWS        → Strands Agent (dual mode:    │
  │               Agent for tool loop,         │
  │               BedrockModel for freeform)   │
  └─────────────────────────────────────────────┘
        │ all providers call same tools
        │
  SharedToolkit (singleton, loaded on startup)
    YAMLIntentLoader → intents/*.yaml
    Tools:
      query_snowflake(sql, warehouse, database, schema)
      cortex_analyst(question, semantic_model_stage_path)
      cortex_complete(prompt, model)
      cortex_summarize(text, model)
      query_bigquery(sql, project_id)
      query_mssql(sql, server, database)
      combine_dataframes(df_a_key, df_b_key, join_key, how)
      ask_clarification(message, candidates)
    DataFrameStore → Redis-backed (session_id:label → DataFrame)
        │
  ┌────┴────────────────┬──────────────────┐
  │ Snowflake           │ BigQuery         │  MSSQL
  │ (SQL + Cortex       │ (ADC auth)       │  (pyodbc)
  │  ANALYST/COMPLETE/  │                  │
  │  SUMMARIZE)         │                  │
  └─────────────────────┴──────────────────┘
        │
  ResponseFormatter (provider LLM writes final answer)
    Returns AgentResponse WS frame:
      explanation: str      ← NL explanation by provider LLM
      table_md: str         ← markdown-formatted table
      csv: str              ← raw CSV data
      sql_used: list[str]   ← SQL queries executed
      python_used: str      ← Python combine code used
```

---

## File Changes

### Modified files (existing) — see updated table under New Files section above

### New files

| File | Purpose |
|------|---------|
| `backend/app/agent/__init__.py` | Module init |
| `backend/app/agent/shared_toolkit.py` | SharedToolkit singleton — tool registration per provider format |
| `backend/app/agent/intent_loader.py` | YAML intent definitions loader + Pydantic schema validation |
| `backend/app/agent/dataframe_store.py` | Redis-backed DataFrame store (`user_id:convo_id:label` key, TTL=3600, JSON serialization) |
| `backend/app/agent/response_formatter.py` | Builds AgentResponse: NL + table_md + csv + sql_used + python_used |
| `backend/app/agent/query_router.py` | Rule-based pre-filter → LLM classification fallback (see Implementation Notes) |
| `backend/app/agent/clarification_state.py` | Redis-backed clarification suspension state (TTL=300) |
| `backend/app/agent/connectors/__init__.py` | Module init |
| `backend/app/agent/connectors/base.py` | BaseConnector ABC — all query methods wrapped in `asyncio.to_thread()` |
| `backend/app/agent/connectors/snowflake_connector.py` | Snowflake SQL + Cortex ANALYST (2-step) + COMPLETE + SUMMARIZE; catches Enterprise-tier error |
| `backend/app/agent/connectors/bigquery_connector.py` | BigQuery with ADC auth (`GOOGLE_APPLICATION_CREDENTIALS`) |
| `backend/app/agent/connectors/mssql_connector.py` | MSSQL via pyodbc; sync wrapped in `asyncio.to_thread()` |
| `backend/app/agent/tools/__init__.py` | Module init |
| `backend/app/agent/tools/query_tools.py` | Canonical tool functions (Pydantic inputs) |
| `backend/app/agent/tools/clarification_tools.py` | `ask_clarification` — writes to clarification_state, sends WS frame |
| `backend/app/agent/tools/combine_tools.py` | DataFrame combine: validates keys exist, handles schema/type mismatches, MAX_ROWS=10000 |
| `backend/config/intents/` | YAML intent definitions (sample files) |
| `backend/config/prompts/` | Markdown LLM prompt files |
| `backend/tests/` | pytest setup + fixtures + unit tests |
| `backend/tests/conftest.py` | Async fixtures, `fakeredis` DataFrameStore patch, mock connectors |
| `backend/tests/test_agent_loop.py` | Provider agent loop correctness tests + empty DataFrame case |
| `backend/tests/test_combine_tools.py` | DataFrame combine: happy path, missing key, schema mismatch, type mismatch, 0-row inputs |
| `backend/tests/test_intent_loader.py` | YAML validation tests |
| `backend/tests/test_clarification_flow.py` | Clarification pause → WS question → user reply → loop resume |
| `backend/tests/test_connectors.py` | Per-connector asyncio.to_thread() integration test |

### Modified files (existing) — updated scope

| File | Change |
|------|--------|
| `backend/app/services/llm/base.py` | Add `run_agent_loop()` with default `raise NotImplementedError` (non-abstract) |
| `backend/app/services/llm/providers/gemini_provider.py` | REPLACE with ADK — class name stays `GeminiProvider` |
| `backend/app/services/llm/providers/anthropic_provider.py` | Add tool_use agent loop with `MAX_TOOL_CALLS=10` cap |
| `backend/app/services/llm/providers/openai_provider.py` | Add function_calling loop with `MAX_TOOL_CALLS=10`; preserve o1/o3 overrides |
| `backend/app/services/llm/providers/aws_provider.py` | Dual mode: Strands Agent for tool loop, BedrockModel unchanged for freeform stream |
| `backend/app/api/routes/chat_ws.py` | Add QueryRouter routing; check `clarification_state` on every incoming message; cancel loop on WS disconnect |
| `backend/app/schemas/ws_messages.py` | Add `AgentResponse` frame + `ClarificationRequest` frame + `AgentProgress` frame |
| `backend/app/core/config.py` | Add REDIS_URL, SNOWFLAKE_*, BIGQUERY_PROJECT_ID, MSSQL_*, GOOGLE_APPLICATION_CREDENTIALS |
| `backend/Dockerfile` | ODBC Driver 18 install BEFORE pip install (see Implementation Notes) |
| `backend/requirements.txt` | Add: google-adk, snowflake-connector-python, google-cloud-bigquery, pyodbc, redis, fakeredis[aioredis], pandas, pyyaml |
| `docker-compose.yml` | Add Redis service |
| `frontend/src/app/core/services/chat-ws.service.ts` | Handle `agent_response` frame: explanation bubble + markdown table + CSV download + collapsible SQL/Python |
| `frontend/src/app/shared/models/chat.models.ts` | Add `AgentResponseFrame`, `ClarificationRequestFrame` TypeScript interfaces |

---

## MVP Scope

### Included
- All 4 provider agent loops (Anthropic, OpenAI, Gemini/ADK, AWS)
- Snowflake connector: SQL + Cortex ANALYST + COMPLETE + SUMMARIZE
- BigQuery connector: ADC auth
- MSSQL connector: pyodbc
- Redis-backed DataFrameStore
- YAML intent definitions + Markdown prompt files
- Cross-agent DataFrame combining (ParallelAgent / parallel tool calls)
- Unknown intent → clarification before DB access
- Response: NL explanation + CSV + formatted table + SQL/Python code
- `AgentResponse` WS frame (new frame type, additive)

### Deferred to v2
- PostgreSQL connector
- MySQL connector
- Snowflake Cortex Search
- Snowflake Cortex Agents REST API
- Redis DataFrameStore → multi-worker horizontal scaling

---

## Known Risks & Edge Cases

### Critical — Must fix before implementation

| ID | Risk | Mitigation |
|----|------|------------|
| A1 | `gemini_provider.py` replacement — `factory.py:102` imports `GeminiProvider` by class name | Replacement class MUST be named `GeminiProvider`; factory.py import unchanged |
| A2 | `run_agent_loop()` as `@abstractmethod` breaks all 4 providers on import during transition | Use default `raise NotImplementedError` (non-abstract); providers opt in |
| A3 | Clarification flow requires WS multi-turn suspension — not modelled in current WS request-response model | Add `pending_clarification` Redis key per session; next WS message for that session resumes waiting loop |
| Q1 | All 3 DB connectors are synchronous — block FastAPI event loop for all concurrent connections | Every connector query call wrapped in `asyncio.to_thread()` |
| T1 | Clarification flow (pause → WS question → resume) has zero test coverage | Add `test_clarification_flow.py` |

### High — Must address before production

| ID | Risk | Mitigation |
|----|------|------------|
| A4 | `session_id` for DataFrameStore as `user_id` only — parallel conversations share DataFrames | Use `f"{user_id}:{conversation_id}"` as all DataFrameStore keys |
| A5 | BigQuery ADC does not auto-resolve in Docker Compose without explicit credential mount | Document: set `GOOGLE_APPLICATION_CREDENTIALS` + volume-mount JSON file OR mount `~/.config/gcloud` |
| A6 | WebSocket disconnect mid-loop — agent continues running with no send destination | Check `websocket.client_state` before each WS send; cancel loop task on disconnect |
| Q2 | Redis pickle serialization = arbitrary code execution risk | Use `df.to_json(orient='split')` write / `pd.read_json(StringIO(s), orient='split')` read |
| Q3 | `cortex_analyst` is 2 operations (REST → SQL, execute SQL) — failure at step 2 must return generated SQL with error | Return `{sql: ..., error: ...}` on step-2 failure, not raw exception |
| Q4 | OpenAI o1/o3 models have tool use restrictions (`max_completion_tokens`, no temperature) | Agent loop extension must preserve existing o1/o3 model-specific overrides from `openai_provider.py:38` |
| Q6 | Redis DataFrameStore TTL unset — unbounded memory growth | `ex=3600` on every `redis.set()` call |
| T2 | Tests require live Redis — `fakeredis` not in plan | Add `fakeredis` to dev deps; patch DataFrameStore in `conftest.py` |
| T3 | Empty DataFrame (0 rows) not tested | Add test: connector returns 0 rows → agent produces "no data found" response, not exception |
| T4 | `asyncio.to_thread()` wrapping must be verified under async test context | Add per-connector integration test confirming no event loop blocking |
| P1 | QueryRouter LLM call adds ~500ms to every freeform message | Rule-based pre-filter (DB keywords, table names from YAML) before LLM classification; LLM fires only when inconclusive |
| P2 | Non-ADK agent loops have no iteration cap — infinite tool call loop on connector error | `MAX_TOOL_CALLS = 10` in every non-ADK loop; log warning + return partial results if cap hit |
| PR1 | Snowflake Cortex ANALYST requires Enterprise tier — Standard tier raises `ProgrammingError` | Catch error, return: `"Cortex Analyst requires Enterprise tier. Use direct SQL instead."` |
| PR2 | ODBC Driver 18 Dockerfile install must run before `pip install` (pyodbc links at install time) | Explicit Dockerfile step order (see Implementation Notes below) |
| PR3 | `GOOGLE_API_KEY` absent → Gemini silently drops from provider list with no user explanation | `is_available()` logs warning; document in `env.template` |
| PR4 | Angular `chat-ws.service.ts` has no `agent_response` frame handler — frame silently dropped | Add `agent_response` frame handling to Angular scope: explanation as bubble, table as markdown, CSV as download link, SQL/Python as collapsible code block |

### Medium — Fix if time permits

| ID | Risk | Mitigation |
|----|------|------------|
| Q5 | `combine_dataframes` edge cases: missing key, column name mismatch, type mismatch, 0-row inputs | Return descriptive error string (not raise) for each case so LLM can decide |
| P3 | Redis serialization overhead for large DataFrames: ~200–450ms per store op | Acceptable within 20s budget; measure and document |
| Agent loop latency | 5–15s for multi-turn (5 LLM round trips + DB queries) | Add typing indicator / progress WS frame during loop |

---

## Implementation Notes

### Dockerfile MSSQL ODBC Driver 18 — correct order
```dockerfile
# Must run BEFORE pip install requirements.txt
RUN apt-get update && apt-get install -y curl gnupg \
  && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
  && curl https://packages.microsoft.com/config/debian/12/prod.list \
     > /etc/apt/sources.list.d/mssql-release.list \
  && apt-get update \
  && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
```

### DataFrameStore Redis key format
```
key: "df:{user_id}:{conversation_id}:{label}"
TTL: 3600 seconds (1 hour)
serialization: df.to_json(orient='split')
deserialization: pd.read_json(StringIO(json_str), orient='split')
```

### Clarification flow WS state
```
Redis key: "clarification:{user_id}:{conversation_id}"
Value: {loop_task_id, candidates, original_query}
TTL: 300 seconds (5 minutes — user must respond within 5 min)
On next WS message for same session: check Redis key first
  → if exists: route message as clarification answer, resume loop
  → if not: treat as new conversation turn
```

### GeminiProvider class name constraint
```python
# gemini_provider.py — replacement file MUST use this class name
class GeminiProvider(BaseLLMProvider):  # NOT ADKProvider
    provider_name = "gemini"
    ...
```

### Non-ADK agent loop iteration cap
```python
MAX_TOOL_CALLS = 10  # applied in anthropic, openai, aws agent loops
```

### QueryRouter pre-filter strategy
```
Step 1 (fast, no LLM): contains YAML intent keywords OR SQL-like patterns?
  → YES: is_data_query = True (skip LLM)
  → NO: is_data_query = False (skip LLM)
  → INCONCLUSIVE: proceed to Step 2
Step 2 (LLM call): classify with confidence threshold
  → confidence >= 0.7: route decision
  → confidence < 0.7: treat as clarification needed
```

---

## Implementation Order

### Phase 1 — Foundation (do first, everything depends on this)
1. `docker-compose.yml` → add Redis service
2. `backend/Dockerfile` → add ODBC Driver 18
3. `backend/requirements.txt` → add all new deps
4. `backend/app/core/config.py` → add new settings
5. `backend/app/agent/tools/query_tools.py` → canonical tool functions
6. `backend/app/agent/intent_loader.py` → YAML loader + Pydantic schema
7. `backend/app/agent/dataframe_store.py` → Redis-backed store
8. `backend/app/agent/connectors/` → 3 connectors (Snowflake, BigQuery, MSSQL)
9. `backend/app/schemas/ws_messages.py` → AgentResponse frame

### Phase 2 — Provider agent loops
10. `backend/app/services/llm/base.py` → add run_agent_loop()
11. `backend/app/services/llm/providers/gemini_provider.py` → replace with ADK
12. `backend/app/services/llm/providers/anthropic_provider.py` → tool_use loop
13. `backend/app/services/llm/providers/openai_provider.py` → function_calling loop
14. `backend/app/services/llm/providers/aws_provider.py` → Strands Agent dual mode
15. `backend/app/agent/shared_toolkit.py` → register tools per provider format

### Phase 3 — Orchestration + response
16. `backend/app/agent/query_router.py` → data query classifier
17. `backend/app/agent/response_formatter.py` → AgentResponse builder
18. `backend/app/api/routes/chat_ws.py` → add QueryRouter + agent loop routing

### Phase 4 — Tests
19. `backend/tests/` → pytest setup + all test files

---

## Mutations Log

| Date | Type | Task | Reason |
|------|------|------|--------|
| 2026-04-19 | Initial | All | Plan created |
| 2026-04-19 | Update | Edge case review | Added 18 edge cases across 5 review phases; updated file list; added Implementation Notes; Angular scope extended to handle AgentResponse/ClarificationRequest frames |
