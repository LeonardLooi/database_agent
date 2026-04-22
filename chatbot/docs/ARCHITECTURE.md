# Architecture — Database Agent Chatbot

This document describes the system architecture, component responsibilities, data flows, and design decisions for the Database Agent Chatbot.

---

## Table of Contents

- [System Overview](#system-overview)
- [Component Map](#component-map)
- [Backend Architecture](#backend-architecture)
  - [API Layer](#api-layer)
  - [LLM Provider Abstraction](#llm-provider-abstraction)
  - [Agentic Orchestration Layer](#agentic-orchestration-layer)
  - [Database Connectors](#database-connectors)
  - [Session State (Redis)](#session-state-redis)
  - [Persistence (SQLite / PostgreSQL)](#persistence-sqlite--postgresql)
- [Frontend Architecture](#frontend-architecture)
- [Data Flows](#data-flows)
  - [Freeform Chat](#freeform-chat)
  - [Data Query (Agent Loop)](#data-query-agent-loop)
  - [Clarification Flow](#clarification-flow)
  - [WebSocket Connection Lifecycle](#websocket-connection-lifecycle)
- [Database Schema](#database-schema)
- [Redis Key Space](#redis-key-space)
- [Configuration Model](#configuration-model)
- [Deployment Topology](#deployment-topology)
- [Key Design Decisions](#key-design-decisions)
- [Known Limitations and Future Work](#known-limitations-and-future-work)

---

## System Overview

```mermaid
graph TB
    subgraph Browser["Browser — Angular 21"]
        UI[Chat UI<br/>Signals + RxJS]
    end

    subgraph Backend["FastAPI Backend — Python 3.12+"]
        WS["/ws/chat<br/>WebSocket handler"]
        Auth["/auth<br/>JWT login"]
        Conv["/conversations<br/>CRUD"]
        QR[QueryRouter]
        LLM[LLMService]
        Loop[Provider Agent Loop]
        ST[SharedToolkit]
        DF[DataFrameStore<br/>Redis / in-memory]
        CS[ClarificationState<br/>Redis]
        RF[ResponseFormatter]
    end

    subgraph Providers["LLM Providers"]
        Claude[Anthropic<br/>tool_use]
        GPT[OpenAI<br/>function_calling]
        Gemini[Google ADK]
        Bedrock[AWS Bedrock<br/>Strands Agent]
    end

    subgraph DBs["Enterprise Databases"]
        SF[Snowflake<br/>+ Cortex]
        BQ[BigQuery]
        MS[MSSQL]
    end

    subgraph Store["Session Storage"]
        Redis[(Redis)]
        SQLite[(SQLite / PostgreSQL)]
    end

    UI -- "HTTP + WebSocket (JWT)" --> WS
    UI -- "HTTP" --> Auth
    UI -- "HTTP" --> Conv
    WS --> QR
    QR -- freeform --> LLM
    QR -- data query --> Loop
    Loop --> ST
    ST --> SF
    ST --> BQ
    ST --> MS
    ST --> DF
    ST --> CS
    Loop --> RF
    LLM --> Claude
    LLM --> GPT
    LLM --> Gemini
    LLM --> Bedrock
    Loop --> Claude
    Loop --> GPT
    Loop --> Gemini
    Loop --> Bedrock
    DF --> Redis
    CS --> Redis
    WS --> SQLite
```

---

## Component Map

```
backend/app/
├── main.py                     # FastAPI app — lifespan, CORS, router registration
├── api/routes/
│   ├── auth.py                 # POST /auth/login, GET /auth/verify
│   ├── chat_ws.py              # WS /ws/chat — orchestration hub (478 lines)
│   ├── conversations.py        # CRUD /conversations, /conversations/{id}/messages
│   └── health.py               # GET /health
├── core/
│   ├── config.py               # Pydantic BaseSettings — all env vars
│   ├── database.py             # AsyncSessionLocal, Base, create_tables()
│   ├── security.py             # JWT create/verify (HS256, 30d expiry)
│   └── ws_manager.py           # Active WebSocket connection pool
├── models/
│   └── conversation.py         # Conversation + Message ORM models
├── schemas/
│   ├── conversation.py         # MessageOut, ConversationOut, ConversationWithMessages
│   └── ws_messages.py          # 10+ WS frame Pydantic schemas
├── services/llm/
│   ├── base.py                 # BaseLLMProvider ABC (stream + run_agent_loop)
│   ├── factory.py              # Provider discovery + registration by API key presence
│   ├── llm_service.py          # Thin orchestrator — selects provider, calls stream()
│   └── providers/
│       ├── anthropic_provider.py   # Claude — tool_use multi-turn loop
│       ├── openai_provider.py      # GPT — function_calling loop (o1/o3 overrides)
│       ├── gemini_provider.py      # Google ADK LlmAgent / ParallelAgent
│       └── aws_provider.py         # Strands Agent dual-mode (agentic + streaming)
└── agent/
    ├── query_router.py         # Intent classification (keyword → LLM fallback)
    ├── intent_loader.py        # YAML intent schema loader + validator
    ├── dataframe_store.py      # Redis-backed DataFrame cache (JSON serialization)
    ├── clarification_state.py  # Redis-backed loop suspension + resume
    ├── response_formatter.py   # WsAgentResponse builder
    ├── shared_toolkit.py       # Canonical tool registry (per-provider formats)
    ├── connectors/
    │   ├── base.py             # BaseConnector ABC
    │   ├── snowflake_connector.py  # SQL + Cortex ANALYST/COMPLETE/SUMMARIZE
    │   ├── bigquery_connector.py   # ADC auth, REST + gRPC client
    │   └── mssql_connector.py      # pyodbc, asyncio.to_thread wrapper
    └── tools/
        ├── query_tools.py      # query_snowflake, query_bigquery, query_mssql, cortex_*
        ├── clarification_tools.py  # ask_clarification (suspends loop, sends WS frame)
        └── combine_tools.py    # combine_dataframes (pandas merge + validation)
```

---

## Backend Architecture

### API Layer

The FastAPI application registers four route groups:

| Route | Module | Purpose |
|-------|--------|---------|
| `POST /auth/login` | `auth.py` | Accepts `{email, password}`, issues 30-day JWT |
| `GET /auth/verify` | `auth.py` | Validates JWT, returns user info |
| `WS /ws/chat` | `chat_ws.py` | Main orchestration — all chat traffic |
| `GET /conversations` | `conversations.py` | List conversations for authenticated user |
| `GET /conversations/{id}` | `conversations.py` | Get conversation with full message history |
| `DELETE /conversations/{id}` | `conversations.py` | Delete conversation and cascade messages |
| `GET /health` | `health.py` | Liveness probe — returns version + provider list |

The WebSocket handler in `chat_ws.py` is the orchestration hub. On each incoming message it:

1. Decodes and validates the JWT (401 disconnect if invalid)
2. Checks `ClarificationState` — if a pending clarification exists, routes as a clarification answer
3. Calls `QueryRouter.is_data_query()` to classify the message
4. Routes to `LLMService.stream()` (freeform) or `provider.run_agent_loop()` (data query)
5. Persists the user message and assistant response to SQLite
6. Sends a `WsTitle` frame with an auto-generated conversation title on first message

### LLM Provider Abstraction

```mermaid
classDiagram
    class BaseLLMProvider {
        <<abstract>>
        +name: str
        +stream(messages, model, system) AsyncIterator~str~
        +run_agent_loop(messages, tools, context) WsAgentResponse
    }
    class AnthropicProvider {
        +name = "anthropic"
        +stream() tool_use multi-turn
        +run_agent_loop() tool_use loop
    }
    class OpenAIProvider {
        +name = "openai"
        +stream() standard streaming
        +run_agent_loop() function_calling loop
    }
    class GeminiProvider {
        +name = "gemini"
        +stream() ADK streaming
        +run_agent_loop() ADK LlmAgent orchestration
    }
    class AWSProvider {
        +name = "aws"
        +stream() Bedrock streaming fallback
        +run_agent_loop() Strands Agent loop
    }
    class LLMProviderFactory {
        +register(provider)
        +get_available() list~BaseLLMProvider~
        +get(name) BaseLLMProvider
    }

    BaseLLMProvider <|-- AnthropicProvider
    BaseLLMProvider <|-- OpenAIProvider
    BaseLLMProvider <|-- GeminiProvider
    BaseLLMProvider <|-- AWSProvider
    LLMProviderFactory --> BaseLLMProvider
```

`LLMProviderFactory` auto-discovers providers at startup by checking whether their respective API keys / credentials are configured. Only available providers are registered and returned to the frontend.

Each provider implements two methods:
- `stream()` — used for freeform chat, yields string tokens
- `run_agent_loop()` — used for data queries, drives the tool-calling loop using the provider's native pattern (tool_use, function_calling, ADK tool definitions, or Strands Agent tools)

### Agentic Orchestration Layer

The agent layer sits between the WebSocket handler and the database connectors.

```mermaid
flowchart TD
    WS["chat_ws.py\n(WebSocket handler)"] --> QR["QueryRouter\nis_data_query()"]
    QR -->|confidence ≥ threshold| Loop["Provider.run_agent_loop()"]
    QR -->|confidence < threshold| CS["ClarificationState.save()"]
    CS -->|WS frame| Client["WsClarificationRequest"]
    Client -->|user picks intent| Resume["ClarificationState.get()\nresume loop"]
    Resume --> Loop

    Loop --> ST["SharedToolkit\ntool registry"]
    ST --> QT["query_tools\nquery_snowflake\nquery_bigquery\nquery_mssql\ncortex_*"]
    ST --> CT["combine_tools\ncombine_dataframes"]
    ST --> Clar["clarification_tools\nask_clarification"]

    QT --> Conn["DB Connectors\nasyncio.to_thread"]
    Conn --> DF["DataFrameStore\n(Redis / in-memory)"]
    CT --> DF

    Loop --> RF["ResponseFormatter"]
    RF --> WsResp["WsAgentResponse"]
```

#### QueryRouter

`QueryRouter` uses a two-stage classification strategy:

1. **Keyword pre-filter** — scans for SQL-like signals (`SELECT`, `revenue`, `sales`, `show me data`, etc.) and intent keywords loaded from YAML files. Returns high-confidence result immediately if a clear match is found.
2. **LLM classification fallback** — when keyword matching is inconclusive, sends a small prompt to the configured LLM to classify intent and assign a confidence score (0.0–1.0).

The router returns an `IntentEstimationResult` with:
- `top_intent` — matched intent name or `"freeform"`
- `confidence` — float 0–1
- `is_ambiguous` — true when confidence falls below threshold
- `candidates` — list of plausible intents (used in clarification request)

#### SharedToolkit

`SharedToolkit` is a singleton initialized at startup. It holds the canonical tool definitions and provides them in the format each provider requires:

| Method | Returns |
|--------|---------|
| `for_anthropic()` | `[{name, description, input_schema: {...}}]` |
| `for_openai()` | `[{name, description, parameters: {...}}]` |
| `for_gemini()` | `google.adk.Tool` objects |
| `for_aws()` | Strands Agent tool format |

All tools share the same Python implementation — the registry just converts the schema.

#### DataFrameStore

Redis-backed (with in-process dict fallback) store for intermediate DataFrames produced by agent tool calls.

```
Key format:  "df:{user_id}:{conversation_id}:{label}"
Value:       df.to_json(orient='split')   ← JSON, not pickle (prevents RCE)
TTL:         3600s (DATAFRAME_TTL_SECONDS)
```

The `{label}` is set by the LLM tool call arguments (e.g., `"sales_data"`, `"products"`) and passed to `combine_dataframes` by the agent.

#### ClarificationState

Suspends the agent loop when intent is ambiguous. Stored in Redis with a 5-minute TTL.

```
Key format:  "clarification:{user_id}:{conversation_id}"
Value:       {loop_task_id, candidates: [], original_query: str}
TTL:         300s (CLARIFICATION_TTL_SECONDS)
```

On the next incoming WS message, `chat_ws.py` checks for a pending clarification before calling `QueryRouter`. If found, the message content is treated as the user's intent selection and the loop is resumed.

#### ResponseFormatter

Builds a `WsAgentResponse` from the agent loop's final state:

- `explanation` — LLM-generated natural language summary
- `table_md` — Markdown-formatted table (first 100 rows; `truncated: true` if more)
- `csv` — Full CSV export for download
- `sql_used` — List of SQL strings executed during the loop
- `python_used` — DataFrame combine code generated by the agent
- `row_count` — Total rows in the final DataFrame

### Database Connectors

All connectors inherit `BaseConnector` and wrap synchronous client libraries in `asyncio.to_thread()`.

```mermaid
classDiagram
    class BaseConnector {
        <<abstract>>
        +execute_query(sql) DataFrame
    }
    class SnowflakeConnector {
        +execute_query(sql, warehouse, database, schema) DataFrame
        +cortex_analyst(question, semantic_model_path) dict
        +cortex_complete(prompt, model) str
        +cortex_summarize(text, model) str
    }
    class BigQueryConnector {
        +execute_query(sql, project_id) DataFrame
    }
    class MSSQLConnector {
        +execute_query(sql, server, database) DataFrame
    }

    BaseConnector <|-- SnowflakeConnector
    BaseConnector <|-- BigQueryConnector
    BaseConnector <|-- MSSQLConnector
```

**Snowflake** additionally supports Cortex APIs:
- `cortex_analyst` — 2-step: send question + semantic model path → get SQL → execute
- `cortex_complete` — Free-form LLM completion (requires Enterprise tier)
- `cortex_summarize` — Text summarization (requires Enterprise tier)

Cortex ANALYST and COMPLETE/SUMMARIZE are guarded with `try/except ProgrammingError` — non-Enterprise accounts receive a clear error message rather than a crash.

**MSSQL** requires ODBC Driver 18 to be installed before `pip install -r requirements.txt`. The Dockerfile handles this order explicitly.

**BigQuery** uses Application Default Credentials (ADC). In Cloud Run, attach a service account with `roles/bigquery.dataViewer`. Locally, run `gcloud auth application-default login`.

### Session State (Redis)

Redis provides two independent namespaces:

| Namespace | Purpose | TTL |
|-----------|---------|-----|
| `df:{user_id}:{conversation_id}:{label}` | DataFrame cache | 3600s |
| `clarification:{user_id}:{conversation_id}` | Loop suspension state | 300s |

When `REDIS_ENABLED=false` (default), both stores fall back to in-process Python dicts. This is sufficient for single-worker deployments (local dev, single Cloud Run instance). For multi-worker production deployments, enable Redis.

### Persistence (SQLite / PostgreSQL)

SQLAlchemy async (via `aiosqlite` for SQLite, `asyncpg` for PostgreSQL) manages all conversation persistence. Alembic handles migrations.

Default: `sqlite+aiosqlite:///./data/chatbot.db`

For Cloud Run production: set `DATABASE_URL` to a Cloud SQL PostgreSQL connection string and add `asyncpg` to `requirements.txt`.

---

## Frontend Architecture

The Angular 21 frontend uses standalone components, Signals for state, and RxJS for the WebSocket stream.

```
src/app/
├── core/services/
│   ├── auth.service.ts         # Login, token storage (localStorage), logout
│   ├── chat-ws.service.ts      # WS lifecycle, frame parsing, Observable streams
│   ├── conversation.service.ts # HTTP CRUD for conversation list
│   ├── providers.service.ts    # Fetch available LLM providers on init
│   └── theme.service.ts        # Dark / light mode toggle
├── features/
│   ├── chat/
│   │   ├── chat-window.component.ts   # Message list, scroll management, markdown render
│   │   └── chat-input.component.ts    # Input field, model selector, submit
│   └── sidebar/
│       └── sidebar.component.ts       # Conversation list, new chat, delete
└── shared/
    ├── components/
    │   └── message-bubble.component.ts  # User/assistant bubble with markdown → HTML
    └── models/
        └── chat.models.ts               # TypeScript interfaces
```

### TypeScript interfaces (chat.models.ts)

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  provider?: string;
  model?: string;
  timestamp: Date;
  agentResponse?: AgentResponseFrame;   // present on data query replies
  clarificationRequest?: ClarificationRequestFrame;
}

interface AgentResponseFrame {
  explanation: string;
  table_md: string;
  csv: string;
  sql_used: string[];
  python_used: string;
  row_count: number;
  truncated: boolean;
}

interface ClarificationRequestFrame {
  message: string;
  candidates: string[];
}
```

### WebSocket service

`chat-ws.service.ts` opens a single persistent WebSocket connection per session. It:

1. Resolves the URL from `window.location` at runtime (works without rebuilding in Docker/Cloud Run)
2. Appends `?token=<jwt>` for authentication
3. Parses each JSON frame by `type` and routes to the appropriate RxJS Subject
4. Reconnects automatically with exponential back-off on unexpected close

---

## Data Flows

### Freeform Chat

```mermaid
sequenceDiagram
    participant Client
    participant WS as chat_ws.py
    participant QR as QueryRouter
    participant LLM as LLMService
    participant Provider

    Client->>WS: WsIncoming {type: "message", content: "Explain WebFlux"}
    WS->>QR: is_data_query("Explain WebFlux")
    QR-->>WS: {top_intent: "freeform", confidence: 0.02}
    WS->>LLM: stream(messages, model, provider)
    LLM->>Provider: stream()
    loop Token streaming
        Provider-->>LLM: token
        LLM-->>WS: token
        WS-->>Client: WsDelta {content: token}
    end
    WS-->>Client: WsDone {token_count, provider, model}
    WS->>SQLite: persist user + assistant messages
```

### Data Query (Agent Loop)

```mermaid
sequenceDiagram
    participant Client
    participant WS as chat_ws.py
    participant QR as QueryRouter
    participant Loop as Provider Agent Loop
    participant ST as SharedToolkit
    participant Conn as DB Connector
    participant DFS as DataFrameStore
    participant RF as ResponseFormatter

    Client->>WS: WsIncoming {content: "Revenue by product for Q1"}
    WS->>QR: is_data_query(content)
    QR-->>WS: {top_intent: "sales_revenue", confidence: 0.88}

    WS->>Loop: run_agent_loop(messages, tools, context)
    Loop-->>Client: WsAgentProgress {step: 1, message: "Analysing query..."}

    Loop->>ST: tool call: query_snowflake("SELECT ...")
    ST->>Conn: execute_query(sql)
    Conn-->>ST: DataFrame (1200 rows)
    ST->>DFS: set("df:u1:c1:revenue_data", df, ttl=3600)
    ST-->>Loop: {rows: 1200, columns: [...], df_key: "revenue_data"}

    Loop-->>Client: WsAgentProgress {step: 2, message: "Fetching product names..."}
    Loop->>ST: tool call: query_snowflake("SELECT product_id, name FROM products")
    ST->>Conn: execute_query(sql)
    Conn-->>ST: DataFrame (50 rows)
    ST->>DFS: set("df:u1:c1:products", df, ttl=3600)

    Loop->>ST: tool call: combine_dataframes("revenue_data", "products", join_key="product_id")
    ST->>DFS: get("revenue_data") + get("products")
    DFS-->>ST: df_a, df_b
    ST-->>Loop: merged DataFrame → DFS.set("combined")

    Loop->>RF: build_response(explanation, ["combined"], sql_list, python_code)
    RF->>DFS: get("combined")
    DFS-->>RF: final DataFrame
    RF-->>Loop: WsAgentResponse

    Loop-->>Client: WsAgentResponse {explanation, table_md, csv, sql_used, python_used}
    WS->>SQLite: persist messages
```

### Clarification Flow

```mermaid
sequenceDiagram
    participant Client
    participant WS as chat_ws.py
    participant QR as QueryRouter
    participant CS as ClarificationState
    participant Loop as Provider Agent Loop

    Client->>WS: WsIncoming {content: "Show me the data"}
    WS->>QR: is_data_query("Show me the data")
    QR-->>WS: {confidence: 0.45, is_ambiguous: true,\n candidates: ["Sales", "Inventory", "CRM"]}

    WS->>CS: save("clarification:u1:c1", {candidates, original_query})
    WS-->>Client: WsClarificationRequest {message: "Which report?", candidates: [...]}

    Note over Client: User clicks "Sales"

    Client->>WS: WsIncoming {content: "Sales"}
    WS->>CS: get("clarification:u1:c1")
    CS-->>WS: {candidates, original_query: "Show me the data"}
    WS->>CS: delete("clarification:u1:c1")

    WS->>Loop: run_agent_loop(messages + selected_intent="Sales")
    Loop-->>Client: WsAgentProgress, WsAgentResponse (normal data flow)
```

### WebSocket Connection Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Connecting: Client opens WS
    Connecting --> Authenticated: JWT valid
    Connecting --> Disconnected: JWT invalid (401)
    Authenticated --> Idle: WsProviders sent
    Idle --> Processing: WsIncoming received
    Processing --> Streaming: freeform path
    Processing --> AgentLoop: data query path
    Processing --> Waiting: clarification pending
    Streaming --> Idle: WsDone sent
    AgentLoop --> Idle: WsAgentResponse sent
    Waiting --> AgentLoop: user resolves clarification
    Idle --> Idle: ping → pong
    Authenticated --> Disconnected: client closes / timeout
    Disconnected --> [*]
```

---

## Database Schema

### conversations

```sql
CREATE TABLE conversations (
    id          VARCHAR PRIMARY KEY,
    user_id     VARCHAR NOT NULL,
    title       VARCHAR DEFAULT 'New Chat',
    created_at  DATETIME NOT NULL,
    updated_at  DATETIME NOT NULL
);
CREATE INDEX ix_conversations_user_id ON conversations (user_id);
```

### messages

```sql
CREATE TABLE messages (
    id                  VARCHAR PRIMARY KEY,
    conversation_id     VARCHAR NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                VARCHAR NOT NULL,   -- 'user' | 'assistant'
    content             TEXT NOT NULL,
    provider            VARCHAR,            -- 'anthropic' | 'openai' | 'gemini' | 'aws'
    model               VARCHAR,
    token_count         INTEGER DEFAULT 0,
    created_at          DATETIME NOT NULL
);
CREATE INDEX ix_messages_conversation_id ON messages (conversation_id);
```

---

## Redis Key Space

| Key pattern | Value type | TTL | Purpose |
|-------------|-----------|-----|---------|
| `df:{user_id}:{conversation_id}:{label}` | JSON string (orient=split) | 3600s | DataFrame cache for agent tool results |
| `clarification:{user_id}:{conversation_id}` | JSON object | 300s | Suspended agent loop + candidate list |

The `{label}` is set by the LLM via tool call arguments. Scoping by `{user_id}:{conversation_id}` prevents cross-conversation data leakage. JSON serialization (not pickle) prevents remote code execution via deserialization.

---

## Configuration Model

`app/core/config.py` uses Pydantic `BaseSettings` with multi-level `.env` resolution. All settings are typed and validated at startup — a missing required value causes immediate failure with a clear error.

```mermaid
graph LR
    ENV[".env file"] --> Settings["Settings (BaseSettings)"]
    OS["OS environment"] --> Settings
    Settings --> Core["SECRET_KEY\nDATABASE_URL\nDEBUG\nCORS_ORIGIN"]
    Settings --> Providers["ANTHROPIC_API_KEY\nOPENAI_API_KEY\nGOOGLE_API_KEY\nAWS_*"]
    Settings --> Redis["REDIS_ENABLED\nREDIS_URL\nDATAFRAME_TTL_SECONDS"]
    Settings --> Agent["MAX_TOOL_CALLS\nMAX_DATAFRAME_ROWS\nINTENT_DIR\nPROMPT_DIR"]
    Settings --> Snowflake["SNOWFLAKE_ACCOUNT\nSNOWFLAKE_USER\nSNOWFLAKE_PASSWORD\n..."]
    Settings --> BigQuery["BIGQUERY_PROJECT_ID\nGOOGLE_APPLICATION_CREDENTIALS"]
    Settings --> MSSQL["MSSQL_SERVER\nMSSQL_DATABASE\nMSSQL_USERNAME\n..."]
```

---

## Deployment Topology

### Local (Docker Compose)

```
docker-compose.yml
├── backend  (port 8000)  — Python FastAPI image
│   └── mounts ./data/ for SQLite persistence
├── frontend (port 4200)  — Angular + nginx image
│   └── proxies /ws → backend:8000
└── redis    (port 6379)  — Redis 7 alpine (optional, enable with REDIS_ENABLED=true)
```

### GCP Cloud Run

```
Artifact Registry
├── backend:latest   → Cloud Run service (backend)
│   ├── Env vars from Secret Manager
│   ├── Optional: Cloud SQL (PostgreSQL) via unix socket
│   └── Optional: Cloud Memorystore (Redis) via VPC connector
└── frontend:latest  → Cloud Run service (frontend)
    └── Env var BACKEND_URL points to backend Cloud Run URL
```

The frontend nginx configuration auto-upgrades `http → https` and `ws → wss` in Cloud Run. The WebSocket URL is resolved at runtime from `window.location`, so no image rebuild is needed when the backend URL changes.

---

## Key Design Decisions

### 1. Provider-native agent loops

Each LLM provider uses its own orchestration pattern rather than a common wrapper. This avoids the lowest-common-denominator problem (losing Anthropic's tool_use streaming or ADK's parallel agent support) at the cost of per-provider implementation effort.

### 2. QueryRouter two-stage classification

Keyword matching is O(1) and handles the majority of clear data queries instantly. The LLM fallback is only invoked for ambiguous cases, keeping median classification latency near zero.

### 3. Redis JSON serialization for DataFrames

DataFrames are serialized with `df.to_json(orient='split')` rather than `pickle`. Pickle deserialization is a known RCE vector — JSON eliminates that risk with minimal overhead for typical DataFrame sizes (<10k rows).

### 4. Redis-optional architecture

`REDIS_ENABLED=false` (default) uses an in-process dict. This makes the project zero-dependency for local development and single-instance deployments while providing a clear migration path to Redis for multi-worker production.

### 5. asyncio.to_thread for sync DB clients

Snowflake, BigQuery, and MSSQL clients are all synchronous. Wrapping calls in `asyncio.to_thread()` keeps the FastAPI event loop unblocked without requiring async rewrites of the connector libraries.

### 6. Auto-resolving WebSocket URL

The Angular service resolves the WebSocket URL from `window.location` at runtime rather than baking it into the build. This means the same Docker image runs identically in `ng serve`, Docker Compose, and Cloud Run without environment-specific builds.

---

## Known Limitations and Future Work

### Deferred to v2

| Item | Reason deferred |
|------|----------------|
| PostgreSQL connector | Not in MVP scope; schema and tooling straightforward to add |
| MySQL connector | Same pattern as MSSQL — deferred for scope |
| Snowflake Cortex Search | Requires semantic index setup outside app scope |
| Snowflake Cortex Agents REST API | New API; deferred until stable |
| Redis DataFrameStore multi-worker scaling | Needs integration testing with Cloud Memorystore |

### Known constraints

| Ref | Constraint |
|-----|-----------|
| A1 | `GeminiProvider` class name must match the factory import exactly |
| A2 | `run_agent_loop()` raises `NotImplementedError` by default (not abstract) to preserve stream-only provider compatibility during transition |
| PR1 | Snowflake Cortex ANALYST / COMPLETE require Enterprise tier — errors are caught and surfaced to the agent as a clear message |
| PR2 | ODBC Driver 18 must be installed before `pip install` in the Dockerfile — order matters |
| Q2 | DataFrameStore uses JSON (not pickle) — this is a deliberate security constraint, not a limitation |
