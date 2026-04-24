# Database Agent AI Chatbot

Python 3.11+, FastAPI, WebSockets, SQLite/PostgreSQL, Redis

A production-ready AI chatbot that connects to Snowflake, BigQuery, and MSSQL databases.
Users ask natural language questions; the agent writes and executes SQL, then returns results
as a markdown table, CSV download, and an LLM-generated explanation.

Supports four LLM backends — Anthropic Claude, OpenAI GPT, Google Gemini, and AWS Bedrock Nova —
with runtime model switching per conversation session.

## Features

- Natural-language → SQL execution across Snowflake, BigQuery, and MSSQL
- Four LLM providers (Anthropic, OpenAI, Gemini, AWS Bedrock) with per-session model switching
- WebSocket streaming: `delta` / `done` / `error` / `agent_response` frame protocol
- YAML skill system for NLP tasks — add skills without touching Python code
- Intent routing with keyword pre-filter and clarification for ambiguous queries
- Session DataFrame store backed by Redis (in-process dict fallback for dev)
- Snowflake Cortex integration: ANALYST (NL→SQL), COMPLETE, and SUMMARIZE
- JWT auth with anonymous guest tokens and named-user tokens
- Four-service Docker Compose stack: nginx → Angular frontend → FastAPI backend → Redis

## Prerequisites

- Python 3.11+ (backend only)
- Docker + Docker Compose (recommended for full-stack deployment)
- At least one LLM API key: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or GCP/AWS credentials

## Quick Start (Docker Compose)

```bash
cd chatbot
cp env.template .env       # fill in API keys and database credentials
docker-compose up -d       # starts nginx, frontend, backend, redis
```

The app is available at `https://localhost`. The self-signed certificate will trigger a browser warning on first visit — accept it to proceed (expected for local dev).

## Local Backend Development

```bash
cd chatbot/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../env.template .env    # fill in API keys
uvicorn app.main:app --reload --port 8080
```

API docs are available at `http://localhost:8080/docs` when `DEBUG=true`.

## Configuration

Copy `env.template` to `.env` and fill in the values. All variables are optional
except those required by your chosen LLM provider and database connectors.

### LLM Providers

| Variable | Description | Required |
|----------|-------------|----------|
| `LLM_PROVIDER` | Default provider: `anthropic`, `openai`, `gemini`, `aws` | Yes |
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude models) | If using Anthropic |
| `OPENAI_API_KEY` | OpenAI API key (GPT models) | If using OpenAI |
| `GCP_IMPERSONATE_SA` | GCP service account email to impersonate (Gemini, Priority 1) | If using Gemini |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service account JSON (Gemini, Priority 2) | If using Gemini |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (Gemini, ADK, BigQuery) | If using Gemini/BigQuery |
| `AWS_REGION` | AWS region for Bedrock (default: `us-east-1`) | If using AWS |
| `AWS_ACCESS_KEY_ID` | AWS access key (falls back to boto3 credential chain) | If using AWS |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | If using AWS |

### Auth

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT signing secret — generate with `openssl rand -hex 32` | insecure default | **Yes in prod** |
| `ALGORITHM` | JWT algorithm | `HS256` | No |
| `ACCESS_TOKEN_EXPIRE_DAYS` | JWT lifetime in days | `30` | No |

The app **refuses to start** in production (`DEBUG=false`) if `SECRET_KEY` is the default value.

### Database (Chat History)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLAlchemy async URL | `sqlite+aiosqlite:///./data/chatbot.db` |

For production, use an async PostgreSQL URL: `postgresql+asyncpg://user:pass@host/db`.

### Redis (Session Store)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_ENABLED` | Enable Redis-backed session stores | `false` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |

**Required for multi-worker deployments.** Without Redis, DataFrames and clarification state
are stored in the worker process and are invisible to other workers.

### Snowflake Connector

| Variable | Description |
|----------|-------------|
| `SNOWFLAKE_ACCOUNT` | Account identifier (e.g. `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Snowflake password |
| `SNOWFLAKE_WAREHOUSE` | Default compute warehouse |
| `SNOWFLAKE_DATABASE` | Default database |
| `SNOWFLAKE_SCHEMA` | Default schema (default: `PUBLIC`) |
| `SNOWFLAKE_ROLE` | Optional role override |

### BigQuery Connector

| Variable | Description |
|----------|-------------|
| `BIGQUERY_PROJECT_ID` | GCP project ID for query billing |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON (shared with Gemini auth) |

### MSSQL Connector

| Variable | Description |
|----------|-------------|
| `MSSQL_SERVER` | SQL Server hostname (e.g. `server.database.windows.net`) |
| `MSSQL_DATABASE` | Database name |
| `MSSQL_USERNAME` | SQL Server username |
| `MSSQL_PASSWORD` | SQL Server password |
| `MSSQL_DRIVER` | ODBC driver name (default: `ODBC Driver 18 for SQL Server`) |

### Agent Limits

| Variable | Description | Default |
|----------|-------------|---------|
| `MAX_TOOL_CALLS` | Maximum tool calls per agent loop turn | `10` |
| `MAX_DATAFRAME_ROWS` | Row cap for all query results | `10000` |
| `DATAFRAME_TTL_SECONDS` | DataFrame session TTL | `3600` |
| `CLARIFICATION_TTL_SECONDS` | Pending clarification TTL | `300` |

## Architecture

```
Browser (WebSocket wss://host/ws/chat?token=<jwt>)
    │
    ▼
nginx (port 443)  ──────────────────────────  Angular frontend (port 80)
    │
    ▼
FastAPI backend (port 8080, internal only)
    │
    ├─ ChatOrchestrator ──► SkillRegistry (YAML skills, hot-reload)
    │       │
    │       └─► QueryRouter (keyword pre-filter → intent match)
    │
    ├─ LLMProviderFactory ──► AnthropicProvider / OpenAIProvider /
    │                         GeminiProvider (ADK) / AWSBedrockProvider (Strands)
    │
    ├─ SharedToolkit ──► query_snowflake / query_bigquery / query_mssql /
    │                    cortex_analyst / combine_dataframes / ask_clarification
    │
    ├─ DataFrameStore  (Redis │ in-process dict)
    ├─ ClarificationState (Redis │ in-process dict)
    └─ SessionModelStore  (Redis │ in-process dict)
```

### WebSocket Message Protocol

The client maintains a single persistent WebSocket connection. All messages are JSON.

**Incoming (client → server):**

| `type` | Required fields | Description |
|--------|----------------|-------------|
| `message` | `messages`, optional `model`, `temperature`, `conversation_id` | Send a chat turn |
| `ping` | — | Keepalive; server replies with `pong` |

**Outgoing (server → client):**

| `type` | Fields | When |
|--------|--------|------|
| `providers` | `data: [{provider, models, default_model}]` | On connect |
| `delta` | `content` | Each streaming token (freeform mode) |
| `done` | `conversation_id`, `token_count`, `provider`, `model` | End of freeform stream |
| `agent_response` | `explanation`, `table_md`, `csv`, `sql_used`, `row_count`, `truncated` | End of agent loop |
| `clarification_request` | `message`, `candidates` | Agent needs user input |
| `title` | `conversation_id`, `title` | First message only, async |
| `error` | `message`, `code` | Any error condition |
| `pong` | — | Reply to ping |

### Routing Flow

```
User message
    │
    ├─ SkillRegistry has skills?
    │       YES → LLM skill-match (confidence 0–1)
    │               ≥ 0.85 → execute_skill() → done frame
    │               0.50–0.85 → clarification_request frame
    │               < 0.50 → fall through
    │
    ├─ QueryRouter.is_data_query() → keyword match
    │       YES → estimate_intent() → ambiguous? → clarification_request
    │             single clear intent → run_agent_loop() → agent_response
    │       NO  → stream() → delta + done
    │
    └─ Clarification pending for this session?
            YES → resume at the clarification type branch above
```

### Adding a New YAML Skill

Create `backend/app/skills/<skill-name>.yaml`:

```yaml
name: summarise_document
description: Summarise a provided document into key bullet points.
instructions: |
  You are a document summariser. The user will provide a document.
  Return a JSON object with a "bullets" array of up to 5 short strings.
parameters:
  max_bullets:
    type: integer
    required: false
    default: 5
    description: Maximum number of bullet points.
output_format: |
  {"bullets": ["point 1", "point 2"]}
tags: [nlp, summarisation]
```

The SkillRegistry picks up the file automatically (watchdog hot-reload in dev, restart in prod).

### Adding a New Intent (Database Query)

Create `backend/config/intents/<intent-name>.yaml`:

```yaml
intents:
  - name: monthly_sales
    description: Monthly sales revenue by product category.
    keywords: [sales, revenue, monthly, category]
    connectors:
      - type: snowflake
        warehouse: COMPUTE_WH
        database: SALES_DB
        schema: PUBLIC
    requires_combine: false
```

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/auth/guest` | Issue anonymous JWT |
| `POST` | `/auth/token` | Issue named-user JWT |
| `GET` | `/api/conversations?token=` | List conversations (most recent 100) |
| `DELETE` | `/api/conversations/{id}?token=` | Delete conversation and messages |
| `GET` | `/api/conversations/{id}/messages?token=` | Get all messages in a conversation |
| `PATCH` | `/api/sessions/{id}/model?token=` | Switch model for a conversation session |
| `GET` | `/health` | Health check — DB connectivity and provider status |
| `WS` | `/ws/chat?token=` | Persistent WebSocket chat connection |

## Testing

```bash
cd backend
pytest                        # all tests
pytest -v tests/              # verbose
pytest --cov=app tests/       # with coverage report
```

## Scripts

All lifecycle scripts live in `chatbot/scripts/` (cross-platform) and `chatbot/` (build entry points).
Run every script from the `chatbot/` directory unless noted otherwise.

### Quick reference

| Goal | macOS / Linux | Windows (PowerShell) |
|------|--------------|----------------------|
| First-time / routine start | `scripts/start.sh` | `scripts\start.ps1` |
| Stop without losing data | `scripts/stop.sh` | `scripts\stop.ps1` |
| Force full rebuild (no cache) | `scripts/rebuild.sh` | `scripts\rebuild.ps1` |
| Build only (enterprise / CI) | `build.sh` | `build.ps1` |
| Check prerequisites | `scripts/check_prereqs.sh` | `scripts\check_prereqs.ps1` |
| Auto-start on Windows boot | — | `scripts\register_startup_task.ps1` *(Admin)* |

### `scripts/start.sh` / `scripts/start.ps1`

The recommended entry point for starting the stack. Runs in two steps:

1. **Prerequisite check** — verifies Docker and `docker-compose` are installed, the Docker daemon is running, and `.env` exists.
2. **Build + start** — delegates to `build.sh` / `build.ps1` (see below), which handles enterprise CA cert injection, proxy settings, image building, and dangling image cleanup.

```bash
# macOS / Linux
cd chatbot
./scripts/start.sh

# Windows PowerShell
cd chatbot
.\scripts\start.ps1
# If blocked by execution policy:
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### `scripts/stop.sh` / `scripts/stop.ps1`

Stops all running containers with `docker-compose down`. Volumes (`sqlite_data`, `redis_data`) are preserved — chat history and Redis state survive the stop.

```bash
./scripts/stop.sh        # macOS / Linux
.\scripts\stop.ps1       # Windows
```

### `scripts/rebuild.sh` / `scripts/rebuild.ps1`

Tears down the stack and forces a completely fresh Docker image build (bypasses the layer cache). Use this when a `pip install` or `npm install` step is stale, or after a dependency version bump.

```bash
./scripts/rebuild.sh     # macOS / Linux — stops, builds --no-cache, starts
.\scripts\rebuild.ps1    # Windows
```

### `build.sh` / `build.ps1`

Low-level build entry point used by `scripts/start.sh` internally. Run this directly when:

- Operating in CI/CD pipelines
- You need to inject a corporate CA certificate or HTTP proxy
- You want the image prune step without the prereq check overhead

**Enterprise setup (one-time):**

```bash
# 1. Copy the example and fill in proxy settings
cp enterprise-build.example .env.build

# 2. Drop your corporate CA certificate
cp /path/to/corp-ca.crt certs/corp-ca.crt

# 3. Build — cert and proxy are injected automatically
./build.sh          # macOS / Linux
.\build.ps1         # Windows
```

Without `certs/corp-ca.crt` and `.env.build`, the build runs as a standard non-enterprise build.

### `scripts/check_prereqs.sh` / `scripts/check_prereqs.ps1`

Standalone prerequisite validator. Called automatically by `start.sh` and `rebuild.sh`. Run manually to diagnose setup issues before attempting a build.

```bash
./scripts/check_prereqs.sh    # exits 0 on success, 1 on failure
.\scripts\check_prereqs.ps1
```

Checks:
- `docker` and `docker-compose` are on `PATH`
- Docker daemon is running
- `chatbot/.env` file exists (warning only if missing)

### `scripts/register_startup_task.ps1` *(Windows Server only)*

Registers a Windows Scheduled Task named `ChatbotDockerStack` that runs `scripts/start.ps1` automatically at system boot. Must be run as Administrator.

```powershell
# Run as Administrator
.\scripts\register_startup_task.ps1

# To remove the task later:
Unregister-ScheduledTask -TaskName 'ChatbotDockerStack' -Confirm:$false
```

### `backend/start.sh` *(local dev only)*

Starts the FastAPI backend in hot-reload mode without Docker. Resolves uvicorn from the local `.venv` first, kills any existing uvicorn process on the target port, then starts with `--reload`.

```bash
cd backend
./start.sh           # port 8080 (default)
./start.sh 8081      # custom port
```

### `backend/docker-entrypoint.sh` *(container internal)*

The Docker `ENTRYPOINT` for the backend container. Not intended to be run manually. On every container start it:

1. Fixes ownership of `/app/data` for the non-root `appuser`.
2. Snapshots every `.db` file to a timestamped backup (retains the 5 most recent).
3. Runs `alembic upgrade head` — exits non-zero if migrations fail, blocking app startup.
4. Executes the container's `CMD` as `appuser` via `gosu`.

## Docker Services

| Service | Image | Ports | Description |
|---------|-------|-------|-------------|
| `nginx` | `chatbot-nginx:latest` | `80:80`, `443:443` | TLS termination, routing, static hosting |
| `frontend` | `chatbot-frontend:latest` | internal `80` | Angular SPA |
| `backend` | `chatbot-backend:latest` | internal `8080` | FastAPI + uvicorn |
| `redis` | `redis:7-alpine` | internal `6379` | DataFrame + clarification state |

The backend is not exposed to the host — nginx is the sole public entry point.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit using conventional commits (`git commit -m 'feat: add feature'`)
4. Push and open a Pull Request against `main`
5. Squash merge — no direct push to `main` or `develop`
