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
- [YAML Skill System](#yaml-skill-system)
- [Sessions API](#sessions-api)
- [WebSocket Protocol](#websocket-protocol)
- [Database Connectors](#database-connectors)
- [Production Deployment (Docker)](#production-deployment-docker)
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
| **YAML skill system** | Extensible skill registry loads `*.yaml` files at startup; `ChatOrchestrator` routes messages to skills before falling back to the database agent or freeform chat; hot-reload via watchdog in dev mode |
| **Per-session model switching** | `PATCH /api/sessions/{id}/model` persists the active model per conversation (Redis-backed, 24-hour TTL, in-memory fallback) |
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
│  │                    ChatOrchestrator                           │ │
│  │  SkillRegistry (YAML) → LLM skill-match → confidence gate    │ │
│  │  CALL_SKILL ≥0.85  ·  CLARIFY 0.50–0.85  ·  GENERIC_ANSWER  │ │
│  └──┬──────────────────────────────────────────────┬────────────┘ │
│     │ skill matched                                 │ no match     │
│  ┌──▼──────────────┐  ┌────────────────────────────▼───────────┐  │
│  │SkillPromptBuild.│  │            QueryRouter                 │  │
│  │ YAML→LLM prompt │  │ keyword pre-filter → LLM classify      │  │
│  └─────────────────┘  └──────────────┬─────────────┬──────────┘  │
│                                       │ data query  │ freeform    │
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
│   │   │   │   ├── orchestrator.py        # ChatOrchestrator (skill → DB agent → chat)
│   │   │   │   ├── routing.py             # Per-provider confidence extraction
│   │   │   │   ├── skill_registry.py      # YAML skill loader with hot-reload
│   │   │   │   ├── skill_prompt_builder.py  # YAML → LLM prompt assembly
│   │   │   │   ├── session_model_store.py   # Per-conversation model preference
│   │   │   │   ├── dataframe_store.py
│   │   │   │   ├── clarification_state.py
│   │   │   │   ├── intent_loader.py
│   │   │   │   ├── query_router.py
│   │   │   │   ├── response_formatter.py
│   │   │   │   └── shared_toolkit.py
│   │   │   ├── skills/           # YAML skill definitions (*.yaml, hot-reloaded)
│   │   │   ├── api/routes/       # auth, chat_ws, conversations, sessions, health
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

Providers without configured credentials are automatically hidden in the model selector.

| Variable | Provider | Notes |
|----------|----------|-------|
| `ANTHROPIC_API_KEY` | Claude (Anthropic) | `sk-ant-...` |
| `OPENAI_API_KEY` | GPT (OpenAI) | `sk-...` |
| `AWS_ACCESS_KEY_ID` | Bedrock (AWS) | Or use IAM role / `~/.aws/credentials` |
| `AWS_SECRET_ACCESS_KEY` | Bedrock (AWS) | — |
| `AWS_REGION` | Bedrock region | `us-east-1` |

### GCP / Gemini Authentication (ADC — no API key)

Gemini uses Application Default Credentials (ADC), not a Google AI Studio API key.
Three auth paths are tried in priority order:

**Priority 1 — Impersonation (production recommended)**

```bash
# Set in .env or as a system environment variable:
GCP_IMPERSONATE_SA=shared-sa@your-project.iam.gserviceaccount.com
```

The caller's ambient identity (Cloud Run SA, Workload Identity, or local gcloud)
impersonates the shared service account. The caller must have
`roles/iam.serviceAccountTokenCreator` on `GCP_IMPERSONATE_SA`.

No key file is needed. Combine with local gcloud for developer machines:

```bash
gcloud auth application-default login
```

**Priority 2 — Service account key file (local dev fallback)**

```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
# Docker: mount the file and set the path inside the container.
```

**Priority 3 — Ambient ADC (last resort — logs a WARNING)**

```bash
gcloud auth application-default login
# No env var required. Identity is whatever gcloud resolved.
# WARNING: the identity may not be the intended shared SA.
```

If all three paths fail, the backend raises `AuthConfigError` at startup with an
actionable remediation message in the logs.

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
| `SKILLS_DIR` | Path to YAML skill definitions loaded by `SkillRegistry` | `./app/skills` |

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

## YAML Skill System

The `ChatOrchestrator` sits in front of every WebSocket message. Before falling back to the database agent or freeform chat, it tries to match the user message against all loaded skills using the active LLM provider.

### Routing decision tree

```
User message
  → ChatOrchestrator._match_skill()  (LLM rates confidence 0.0–1.0)
      ├─ confidence ≥ 0.85  → CALL_SKILL: execute skill, return SkillResult
      ├─ confidence 0.50–0.84 → CLARIFY: ask user to confirm intent
      └─ confidence < 0.50  → GENERIC_ANSWER:
              ├─ QueryRouter says data query → Provider agent loop (DB tools)
              └─ otherwise → LLMService.stream() (freeform)
```

### Adding a skill

Drop a YAML file into `chatbot/backend/app/skills/`. It is hot-reloaded at runtime (watchdog must be installed):

```yaml
name: my_skill
description: >
  One sentence describing what this skill does — the LLM reads this to decide whether to route here.
instructions: |
  You are an expert at… (full system prompt for the skill executor)
parameters:
  input_text:
    type: string
    required: true
    description: The text to process
output_format: |
  {"result": "...", "confidence": 0.0}
tags: [analysis, text]
```

| Field | Required | Purpose |
|-------|----------|---------|
| `name` | Yes | Unique skill identifier (used in logs and routing) |
| `description` | Yes | One sentence read by the LLM skill-matcher |
| `instructions` | Yes | Full system prompt executed by the active provider |
| `parameters` | No | Named inputs extracted from the user message |
| `output_format` | No | JSON schema the LLM must follow in its response |
| `tags` | No | Reserved for future tag-based pre-filtering (>30 skills) |

### Confidence signals by provider

| Provider | Signal | Optional enhancement |
|----------|--------|---------------------|
| Anthropic | Self-reported float in JSON | Follow-up self-eval prompt (`ENABLE_ANTHROPIC_SELF_EVAL=true`) |
| OpenAI | Self-reported float in JSON | logprobs averaging (`ENABLE_LOGPROB_CONFIDENCE=true`) |
| Gemini | Self-reported float, or keyword-overlap heuristic (fallback when 0.0) | — |

---

## Sessions API

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `PATCH /api/sessions/{session_id}/model` | Bearer JWT (query param `?token=`) | Switch the active model mid-conversation without losing history |

**Request body:**
```json
{ "model": "claude-opus-4-7" }
```

**Response:**
```json
{ "model": "claude-opus-4-7", "provider": "anthropic", "session_id": "..." }
```

The preference is persisted in Redis (or in-process dict) with a 24-hour TTL.

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

## Production Deployment (Docker)

The stack is fully containerised and runs on any host that supports Docker Compose v2 — VPS, bare metal, AWS EC2, DigitalOcean, Azure VM, etc. nginx is the single public entry point; backend and frontend are never exposed directly.

```
nginx (port 80/443) ─── frontend (port 80, internal)
                    └── backend  (port 8000, internal)
                              └── redis (port 6379, internal)
                              └── sqlite_data / postgres (volume)
```

### 1 — Prepare the server

Install Docker Engine and Compose v2 on your host:

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # log out and back in
docker compose version           # should print v2.x
```

Clone the repo and enter the chatbot directory:

```bash
git clone <your-repo-url>
cd database_agent/chatbot
```

### 2 — Configure environment

```bash
cp env.template .env
```

Edit `.env`. Minimum required values:

```bash
SECRET_KEY=$(openssl rand -hex 32)   # paste the output into .env
ANTHROPIC_API_KEY=sk-ant-...         # at least one LLM key required
CORS_ORIGIN=https://your-domain.com  # must match the public URL
REDIS_ENABLED=true                   # enable for production (multi-worker safe)
REDIS_URL=redis://redis:6379/0       # matches the redis service in docker-compose.yml
```

Never commit `.env` — it contains secrets.

### 3 — Build and start

```bash
docker compose up --build -d
```

This builds all images locally and starts four services: `redis`, `backend`, `frontend`, `nginx`. nginx listens on port 80. Check that everything is healthy:

```bash
docker compose ps
docker compose logs backend --tail 50
curl http://localhost/health          # should return {"status":"ok",...}
```

### 4 — HTTPS with a reverse proxy (recommended)

Run nginx or Caddy on the host as a TLS terminator in front of the Compose stack:

**Option A — Caddy (simplest, auto-HTTPS)**

Install Caddy on the host, then create `/etc/caddy/Caddyfile`:

```
your-domain.com {
    reverse_proxy localhost:80
}
```

```bash
sudo systemctl reload caddy
```

Caddy automatically obtains and renews a Let's Encrypt certificate.

**Option B — nginx on the host**

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass          http://localhost:80;
        proxy_http_version  1.1;
        proxy_set_header    Upgrade $http_upgrade;
        proxy_set_header    Connection "upgrade";
        proxy_set_header    Host $host;
        proxy_read_timeout  3600s;   # required for long-lived WebSocket connections
    }
}
```

Use `certbot --nginx -d your-domain.com` to obtain the certificate.

After adding TLS, update `CORS_ORIGIN` in `.env` to the `https://` URL and restart:

```bash
docker compose up -d --no-build
```

### 5 — Persistent database (PostgreSQL)

SQLite is fine for a single host. For multiple replicas or managed backup, switch to PostgreSQL:

```bash
# On the host (or use a managed DB service)
docker run -d \
  --name chatbot-postgres \
  -e POSTGRES_DB=chatbot \
  -e POSTGRES_USER=chatbot \
  -e POSTGRES_PASSWORD=YOUR_DB_PASSWORD \
  -v pg_data:/var/lib/postgresql/data \
  -p 5432:5432 \
  postgres:15-alpine
```

Then set in `.env`:

```bash
DATABASE_URL=postgresql+asyncpg://chatbot:YOUR_DB_PASSWORD@host.docker.internal:5432/chatbot
```

Add `asyncpg` to `chatbot/backend/requirements.txt` before rebuilding. Run Alembic migrations on first deploy:

```bash
docker compose run --rm backend alembic upgrade head
```

### 6 — Updating the deployment

```bash
git pull
docker compose up --build -d   # rebuilds changed images, replaces containers
docker compose image prune -f  # remove dangling old images
```

### Environment routing reference

| Mode | Entry point | WebSocket URL resolved from | Backend |
|------|------------|----------------------------|---------|
| `npm start` (local dev) | `localhost:4200` | `proxy.conf.json` → `localhost:8000` | direct |
| Docker Compose (HTTP) | `localhost:80` via nginx | `window.location` → `ws://localhost` | `http://backend:8000` (internal) |
| Docker Compose + TLS | `your-domain.com:443` via host proxy | `window.location` → `wss://your-domain.com` | `http://backend:8000` (internal) |

The frontend resolves the WebSocket URL from `window.location` at runtime — the same Docker image works in all three modes without rebuilding.

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
| `test_auth.py` | JWT login, token validation, expiry |
| `test_clarification_flow.py` | Ambiguous query → WS request → resume |
| `test_combine_tools.py` | DataFrame merge edge cases |
| `test_integration.py` | End-to-end WebSocket message flow |
| `test_intent_clarification_integration.py` | End-to-end intent + clarification |
| `test_intent_loader.py` | YAML intent parsing and validation |
| `test_orchestrator.py` | ChatOrchestrator skill-match, confidence routing, CALL_SKILL/CLARIFY/GENERIC paths |
| `test_providers.py` | LLM provider adapters (Anthropic, OpenAI, Gemini) |
| `test_query_router.py` | Data query classification (keyword + LLM) |
| `test_routing.py` | Per-provider confidence extraction (enhance_gemini, enhance_openai, enhance_anthropic) |
| `test_session_model.py` | SessionModelStore get/set with in-memory and Redis backends |
| `test_skill_registry.py` | SkillRegistry load, validation, reload |
| `test_stress.py` | Concurrent WebSocket connection handling |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit using conventional commits: `git commit -m 'feat: add feature'`
4. Push and open a Pull Request against `main`
5. Squash merge only — keep history clean

This repo ships pre-configured Claude Code agents, skills, slash commands, and MCP server integrations. See `CLAUDE.md` for the full developer workflow and `.claude/skills/` for per-technology coding patterns.
