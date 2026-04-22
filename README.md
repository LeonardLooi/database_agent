# Database Agent Chatbot

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![Angular](https://img.shields.io/badge/angular-21.x-red)
![FastAPI](https://img.shields.io/badge/fastapi-latest-green)

A production-grade, full-stack AI chatbot with an **agentic data query engine**. The backend (Python/FastAPI) orchestrates multiple LLM providers — Anthropic, OpenAI, Google Gemini (via ADK), and AWS Bedrock — and can autonomously query enterprise databases (Snowflake, BigQuery, MSSQL), combine results across sources, and return structured responses with tables, CSV exports, and the SQL that was run. The Angular 21 frontend streams responses over WebSocket in real time.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Agentic Data Query Flow](#agentic-data-query-flow)
- [WebSocket Protocol](#websocket-protocol)
- [Database Connectors](#database-connectors)
- [Deploy to GCP Cloud Run](#deploy-to-gcp-cloud-run)
- [Testing](#testing)
- [Contributing](#contributing)

---

## Features

| Feature | Detail |
|---------|--------|
| **Multi-provider LLM** | Anthropic Claude, OpenAI GPT, Google Gemini (ADK), AWS Bedrock (Strands Agent) — only providers with configured API keys appear in the UI |
| **Agentic data querying** | Autonomous tool-calling loop queries Snowflake, BigQuery, and MSSQL; combines DataFrames across sources |
| **Intent routing** | `QueryRouter` classifies each message as data query or freeform via keyword rules + LLM fallback |
| **Clarification flow** | Ambiguous queries suspend the agent loop and ask the user to pick an intent; loop resumes on reply |
| **Real-time streaming** | Freeform responses stream token-by-token over WebSocket; data responses stream progress frames |
| **Structured agent responses** | Agent replies include NL explanation, Markdown table, CSV download, and executed SQL |
| **Snowflake Cortex** | Native support for Cortex ANALYST (semantic-model SQL generation), COMPLETE, and SUMMARIZE |
| **DataFrame session cache** | Redis-backed (in-memory fallback) session store for intermediate query results; TTL-scoped per conversation |
| **JWT authentication** | 30-day token expiry, bearer-token WebSocket auth |
| **Persistent history** | Conversations and messages stored in SQLite (swappable to PostgreSQL via env var) |
| **Docker-native** | Single `docker compose up --build` for full local environment |
| **GCP Cloud Run ready** | Backend and frontend each ship as a Docker image; Cloud SQL optional for persistent storage |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Browser (Angular 21)                         │
│  ┌──────────┐  ┌─────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  Sidebar │  │ Chat Window │  │ Chat Input │  │Model Selector│  │
│  └──────────┘  └─────────────┘  └────────────┘  └──────────────┘  │
│        │              │                │                │           │
│        └──────────────┴────────────────┴────────────────┘          │
│                              HTTP + WebSocket (JWT)                 │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────┐
│                     FastAPI Backend (Python 3.12+)                  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  /auth       │  │  /conversations  │  │  /ws/chat (WS)       │  │
│  │  JWT login   │  │  CRUD history    │  │  Orchestration hub   │  │
│  └──────────────┘  └──────────────────┘  └──────────┬───────────┘  │
│                                                      │              │
│  ┌───────────────────────────────────────────────────▼───────────┐ │
│  │                      QueryRouter                              │ │
│  │  keyword pre-filter → LLM classification (confidence score)  │ │
│  └──────────────────┬─────────────────────────┬─────────────────┘ │
│                     │ data query              │ freeform           │
│  ┌──────────────────▼──────────────┐  ┌──────▼──────────────────┐ │
│  │    Provider Agent Loop          │  │   LLMService.stream()   │ │
│  │  ┌────────────────────────────┐ │  │   Token delta frames    │ │
│  │  │ SharedToolkit              │ │  └─────────────────────────┘ │
│  │  │  · query_snowflake         │ │                              │
│  │  │  · cortex_analyst          │ │                              │
│  │  │  · query_bigquery          │ │                              │
│  │  │  · query_mssql             │ │                              │
│  │  │  · combine_dataframes      │ │                              │
│  │  │  · ask_clarification       │ │                              │
│  │  └───────────┬────────────────┘ │                              │
│  │              │                  │                              │
│  │  ┌───────────▼────────────────┐ │                              │
│  │  │ DataFrameStore (Redis/mem) │ │                              │
│  │  │ ClarificationState (Redis) │ │                              │
│  │  └────────────────────────────┘ │                              │
│  └─────────────────────────────────┘                              │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  LLM Providers (BaseLLMProvider)                           │   │
│  │  Anthropic (tool_use) │ OpenAI (function_calling)          │   │
│  │  Gemini (Google ADK)  │ AWS (Strands Agent)                │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │  DB Connectors (asyncio.to_thread wrapped)                 │   │
│  │  SnowflakeConnector │ BigQueryConnector │ MSSQLConnector   │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                    │
│  SQLite / PostgreSQL (conversations + messages)                    │
│  Redis (DataFrameStore + ClarificationState)                       │
└────────────────────────────────────────────────────────────────────┘
```

See [`chatbot/docs/ARCHITECTURE.md`](chatbot/docs/ARCHITECTURE.md) for detailed component descriptions, Mermaid diagrams, data flow walkthroughs, and database schemas.

---

## Project Structure

```
database_agent/
├── chatbot/
│   ├── backend/                  # Python FastAPI backend
│   │   ├── app/
│   │   │   ├── agent/            # Agentic orchestration layer
│   │   │   │   ├── connectors/   # Snowflake, BigQuery, MSSQL adapters
│   │   │   │   ├── tools/        # query_tools, clarification_tools, combine_tools
│   │   │   │   ├── dataframe_store.py
│   │   │   │   ├── clarification_state.py
│   │   │   │   ├── intent_loader.py
│   │   │   │   ├── query_router.py
│   │   │   │   ├── response_formatter.py
│   │   │   │   └── shared_toolkit.py
│   │   │   ├── api/routes/       # auth, chat_ws, conversations, health
│   │   │   ├── core/             # config, database, security, ws_manager
│   │   │   ├── models/           # SQLAlchemy ORM (Conversation, Message)
│   │   │   ├── schemas/          # Pydantic v2 schemas (ws_messages, conversation)
│   │   │   ├── services/llm/     # BaseLLMProvider + Anthropic/OpenAI/Gemini/AWS
│   │   │   └── main.py
│   │   ├── config/
│   │   │   ├── intents/          # YAML intent definitions
│   │   │   └── prompts/          # Markdown prompt templates
│   │   ├── tests/                # pytest suite (agent loop, clarification, combine, router)
│   │   ├── alembic/              # DB migrations
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── start.sh
│   ├── frontend/                 # Angular 21 SPA
│   │   ├── src/app/
│   │   │   ├── core/services/    # auth, chat-ws, conversation, providers, theme
│   │   │   ├── features/         # chat/, sidebar/
│   │   │   └── shared/           # components/, models/
│   │   ├── Dockerfile
│   │   └── package.json
│   ├── docs/
│   │   ├── ARCHITECTURE.md       # Deep-dive architecture docs + Mermaid diagrams
│   │   └── plans/                # Approved MVP implementation plans
│   ├── docker-compose.yml
│   └── env.template
├── .claude/                      # Claude Code agents, skills, hooks, rules
├── blackbox/                     # Append-only session audit logs
├── CLAUDE.md                     # Developer workflow guide
└── README.md                     # This file
```

---

## Prerequisites

**Docker path (recommended):**
- Docker Desktop or Docker Engine with Compose v2

**Local development path:**
- Python 3.12+
- Node.js 20+ and npm 10+
- At least one LLM API key (Anthropic, OpenAI, Google, or AWS)

**Optional (for database connectors):**
- Snowflake account with `ACCOUNTADMIN` or equivalent role
- Google Cloud credentials (`gcloud auth application-default login`) for BigQuery
- SQL Server 2019+ with ODBC Driver 18 for MSSQL

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
cd chatbot
cp env.template .env          # then edit .env — set at least one LLM API key and SECRET_KEY
docker compose up --build
```

- Frontend: http://localhost:4200
- Backend API docs: http://localhost:8000/docs _(only when `DEBUG=true`)_

### Option B — Local (no Docker)

```bash
# 1. Backend
cd chatbot/backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../env.template ../.env    # edit .env

# Recommended start script (handles port cleanup):
./start.sh
# Or manually:
uvicorn app.main:app --reload --port 8000

# 2. Frontend (new terminal)
cd chatbot/frontend
npm install
npm start
```

- Frontend: http://localhost:4200
- Backend: http://localhost:8000

---

## Configuration

Copy `chatbot/env.template` to `chatbot/.env`. At minimum, set `SECRET_KEY` and one LLM API key.

### Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT signing secret — generate with `openssl rand -hex 32` | dev placeholder | **Yes** |
| `LLM_PROVIDER` | Default provider: `anthropic` \| `openai` \| `gemini` \| `aws` | first available | No |
| `DATABASE_URL` | SQLAlchemy async URL | `sqlite+aiosqlite:///./data/chatbot.db` | No |
| `DEBUG` | Enable `/docs` and verbose logging | `false` | No |
| `CORS_ORIGIN` | Allowed CORS origin for frontend | `http://localhost:4200` | No |
| `WS_HEARTBEAT_INTERVAL` | WebSocket ping interval in seconds | `25` | No |
| `APP_VERSION` | Version string returned by `/health` | `1.0.0` | No |

### LLM Provider Keys

Providers without a configured key (or valid AWS credentials) are automatically hidden in the model selector.

| Variable | Provider | Notes |
|----------|----------|-------|
| `ANTHROPIC_API_KEY` | Claude (Anthropic) | `sk-ant-...` |
| `OPENAI_API_KEY` | GPT (OpenAI) | `sk-...` |
| `GOOGLE_API_KEY` | Gemini (Google ADK) | From Google AI Studio |
| `AWS_ACCESS_KEY_ID` | Bedrock (AWS) | Or use IAM role / `~/.aws/credentials` |
| `AWS_SECRET_ACCESS_KEY` | Bedrock (AWS) | — |
| `AWS_REGION` | Bedrock region | `us-east-1` |

### Redis (Session State)

Redis is optional. When disabled, DataFrameStore uses an in-process dict (single-worker only).

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_ENABLED` | Enable Redis | `false` |
| `REDIS_URL` | Connection URL | `redis://localhost:6379/0` |
| `DATAFRAME_TTL_SECONDS` | DataFrame cache TTL | `3600` |
| `CLARIFICATION_TTL_SECONDS` | Clarification state timeout | `300` |

### Agent Limits

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_TOOL_CALLS` | Max tool-call iterations per agent loop | `10` |
| `MAX_DATAFRAME_ROWS` | Max rows fetched per DB query | `10000` |
| `INTENT_DIR` | Path to YAML intent definitions | `./config/intents` |
| `PROMPT_DIR` | Path to Markdown prompt templates | `./config/prompts` |

### Database Connectors

Leave connector variables empty to disable the connector — it simply won't be available to the agent.

**Snowflake:**

| Variable | Description | Default |
|----------|-------------|---------|
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) | — |
| `SNOWFLAKE_USER` | Username | — |
| `SNOWFLAKE_PASSWORD` | Password | — |
| `SNOWFLAKE_WAREHOUSE` | Default warehouse | `COMPUTE_WH` |
| `SNOWFLAKE_DATABASE` | Default database | — |
| `SNOWFLAKE_SCHEMA` | Default schema | `PUBLIC` |
| `SNOWFLAKE_ROLE` | Role override | — |

> **Note:** Cortex ANALYST and Cortex COMPLETE require Snowflake Enterprise tier or higher.

**BigQuery:**

| Variable | Description |
|----------|-------------|
| `BIGQUERY_PROJECT_ID` | GCP project ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (optional if using ADC) |

**MSSQL:**

| Variable | Description | Default |
|----------|-------------|---------|
| `MSSQL_SERVER` | SQL Server host | — |
| `MSSQL_DATABASE` | Database name | — |
| `MSSQL_USERNAME` | Username | — |
| `MSSQL_PASSWORD` | Password | — |
| `MSSQL_DRIVER` | ODBC driver name | `ODBC Driver 18 for SQL Server` |

---

## Agentic Data Query Flow

When a user sends a message, the `QueryRouter` classifies it as either a **data query** or a **freeform question**.

### Freeform path

```
User message → QueryRouter (freeform) → LLMService.stream() → WsDelta frames (tokens) → WsDone
```

### Data query path

```
User message → QueryRouter (data query)
  → Provider.run_agent_loop()
      ├─ Iteration 1: LLM calls query_snowflake("SELECT revenue BY month...")
      │   └─ SnowflakeConnector → DataFrame → DataFrameStore.set("sales_data")
      ├─ Iteration 2: LLM calls query_snowflake("SELECT product_name...")
      │   └─ DataFrameStore.set("products")
      ├─ Iteration 3: LLM calls combine_dataframes("sales_data", "products", join_key="product_id")
      │   └─ pandas merge → DataFrameStore.set("combined")
      └─ Final: LLM generates natural language explanation
  → ResponseFormatter builds WsAgentResponse:
      ├─ explanation: "Revenue increased 23% YoY, led by Product A..."
      ├─ table_md: Markdown table (first 100 rows)
      ├─ csv: Full CSV export
      ├─ sql_used: ["SELECT...", "SELECT..."]
      └─ python_used: "df.merge(sales, products, on='product_id')"
```

### Clarification flow

When the `QueryRouter` cannot confidently route a query (confidence < threshold), it suspends the agent loop and asks the user to pick an intent:

```
Ambiguous message → QueryRouter (confidence=0.45, candidates=["Sales","Inventory","CRM"])
  → ClarificationState.save() → WsClarificationRequest frame → UI shows choice buttons
  → User picks "Sales Report"
  → ClarificationState.get() → resume agent loop with selected intent
  → Normal data query path from here
```

---

## WebSocket Protocol

All communication with `/ws/chat` uses JSON frames validated by Pydantic schemas.

**Connection:** `ws://host/ws/chat?token=<jwt_token>`

### Incoming frames (Client → Backend)

| `type` | Payload | Purpose |
|--------|---------|---------|
| `message` | `content`, `model`, `provider`, `conversation_id` | Send chat message |
| `ping` | — | Keepalive |

### Outgoing frames (Backend → Client)

| `type` | Payload | Trigger |
|--------|---------|---------|
| `providers` | `providers: [{id, name, models[]}]` | On connection — list available LLM providers |
| `delta` | `content: string` | Streaming token (freeform path) |
| `done` | `token_count, provider, model` | End of freeform stream |
| `agent_progress` | `step, total, message` | Progress during agent loop |
| `agent_response` | `explanation, table_md, csv, sql_used, python_used, row_count, truncated` | Final agent answer |
| `clarification_request` | `message, candidates: string[]` | Agent needs user to disambiguate intent |
| `title` | `title: string` | Auto-generated conversation title |
| `error` | `message, code` | Error with recoverable code |
| `pong` | — | Response to `ping` |

---

## Database Connectors

All connectors wrap synchronous client libraries in `asyncio.to_thread()` for non-blocking execution.

| Connector | Authentication | Notes |
|-----------|---------------|-------|
| **Snowflake** | Username + password | Also supports Cortex ANALYST (semantic-model → SQL), COMPLETE, SUMMARIZE |
| **BigQuery** | Application Default Credentials (ADC) or service account JSON | Requires `BIGQUERY_PROJECT_ID` |
| **MSSQL** | Username + password via pyodbc | Requires ODBC Driver 18 installed; Dockerfile installs it before pip |

### Supported agent tools

| Tool | Description |
|------|-------------|
| `query_snowflake(sql, warehouse, database, schema)` | Execute SQL on Snowflake, return DataFrame |
| `cortex_analyst(question, semantic_model_path)` | Natural-language → SQL via Cortex ANALYST |
| `cortex_complete(prompt, model)` | Snowflake Cortex LLM completion |
| `cortex_summarize(text, model)` | Snowflake Cortex summarization |
| `query_bigquery(sql, project_id)` | Execute SQL on BigQuery, return DataFrame |
| `query_mssql(sql, server, database)` | Execute SQL on SQL Server, return DataFrame |
| `combine_dataframes(df_a_key, df_b_key, join_key, how)` | pandas merge of two cached DataFrames |
| `ask_clarification(message, candidates)` | Suspend loop and request user selection |

---

## Deploy to GCP Cloud Run

### 1 — One-time setup

```bash
export PROJECT_ID=YOUR_PROJECT_ID
export REGION=asia-southeast1        # change to your region
export REPO=chatbot

gcloud config set project $PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com

gcloud artifacts repositories create $REPO \
  --repository-format=docker \
  --location=$REGION

gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### 2 — Store secrets in Secret Manager

```bash
echo -n "your-anthropic-key"         | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "your-openai-key"            | gcloud secrets create OPENAI_API_KEY    --data-file=-
echo -n "your-google-key"            | gcloud secrets create GOOGLE_API_KEY    --data-file=-
echo -n "$(openssl rand -hex 32)"    | gcloud secrets create SECRET_KEY        --data-file=-
```

Leave any key empty (`echo -n ""`) if you don't use that provider — it won't appear in the UI.

### 3 — Build and deploy the backend

```bash
cd chatbot/backend

docker build --platform linux/amd64 \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest

gcloud run deploy backend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/backend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=8000 \
  --timeout=3600 \
  --concurrency=80 \
  --set-secrets="ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,SECRET_KEY=SECRET_KEY:latest" \
  --set-env-vars="REDIS_ENABLED=false,CORS_ORIGIN=https://PLACEHOLDER"

BACKEND_URL=$(gcloud run services describe backend \
  --region=$REGION --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

### 4 — Build and deploy the frontend

```bash
cd chatbot/frontend

docker build --platform linux/amd64 \
  -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest

gcloud run deploy frontend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/frontend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --port=80 \
  --set-env-vars="BACKEND_URL=${BACKEND_URL}"

FRONTEND_URL=$(gcloud run services describe frontend \
  --region=$REGION --format='value(status.url)')
echo "Frontend URL: $FRONTEND_URL"
```

### 5 — Update backend CORS

```bash
gcloud run services update backend \
  --region=$REGION \
  --update-env-vars="CORS_ORIGIN=${FRONTEND_URL}"
```

### 6 — Persistent database (optional but recommended)

Cloud Run is stateless — SQLite data is lost on every redeploy. Use Cloud SQL for production:

```bash
gcloud sql instances create chatbot-db \
  --database-version=POSTGRES_15 \
  --region=$REGION \
  --tier=db-f1-micro

gcloud sql databases create chatbot --instance=chatbot-db
gcloud sql users create chatbot --instance=chatbot-db --password=YOUR_DB_PASSWORD
```

Redeploy the backend with:

```bash
--add-cloudsql-instances=${PROJECT_ID}:${REGION}:chatbot-db \
--set-env-vars="DATABASE_URL=postgresql+asyncpg://chatbot:PASSWORD@/chatbot?host=/cloudsql/${PROJECT_ID}:${REGION}:chatbot-db"
```

Add `asyncpg` to `requirements.txt` before rebuilding.

### Environment routing reference

| Mode | Angular env | WebSocket target | Backend |
|------|------------|-----------------|---------|
| `npm start` (local) | `environment.ts` | `ws://localhost:4200` via `proxy.conf.json` | `localhost:8000` |
| Docker Compose | `environment.prod.ts` | `ws://localhost:4200` via nginx | `http://backend:8000` |
| Cloud Run | `environment.prod.ts` | `wss://frontend-url` via nginx | `https://backend-xxx.run.app` |

The frontend auto-resolves the WebSocket URL from `window.location` so the same Docker image works in all three environments without rebuilding.

---

## Testing

```bash
# Backend — from chatbot/backend/
source .venv/bin/activate
pytest                              # all tests
pytest --cov=app                    # with coverage report
pytest -k test_agent_loop           # single test file
pytest -k test_clarification_flow   # clarification flow tests

# Frontend — from chatbot/frontend/
ng test                             # unit tests (Karma, watch mode)
ng test --no-watch --code-coverage  # single run with coverage
```

### Test coverage areas

| Test file | What it covers |
|-----------|---------------|
| `test_agent_loop.py` | Provider-specific agent loop correctness |
| `test_clarification_flow.py` | Ambiguous query → WS request → resume |
| `test_combine_tools.py` | DataFrame merge edge cases |
| `test_intent_clarification_integration.py` | End-to-end intent + clarification |
| `test_intent_loader.py` | YAML intent parsing and validation |
| `test_query_router.py` | Data query classification (keyword + LLM) |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit using conventional commits: `git commit -m 'feat: add feature'`
4. Push and open a Pull Request against `main`
5. Squash merge only — keep history clean

This repo ships pre-configured Claude Code agents, skills, slash commands, and MCP server integrations. See `CLAUDE.md` for the full developer workflow and `.claude/skills/` for per-technology coding patterns.
