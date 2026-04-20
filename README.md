# Database Agent Chatbot

A full-stack AI chatbot with a **Python/FastAPI** backend and **Angular** frontend, supporting multiple LLM providers (Anthropic, OpenAI, Google Gemini, AWS Bedrock). Conversations are persisted in SQLite and streamed to the browser over WebSockets.

## Architecture

```
chatbot/
├── backend/          # Python 3 · FastAPI · SQLAlchemy async · SQLite
│   └── app/
│       ├── api/routes/       # auth, chat (WebSocket), conversations, health
│       ├── services/llm/     # provider abstraction + Anthropic/OpenAI/Gemini/AWS adapters
│       ├── models/           # SQLAlchemy ORM models
│       └── schemas/          # Pydantic v2 request/response schemas
└── frontend/         # Angular · TypeScript · Tailwind CSS
    └── src/app/
        ├── core/             # auth, API client, WebSocket service
        ├── features/         # chat UI, conversation list
        └── shared/           # reusable components
```

## Features

- Multi-provider LLM support — only providers with configured API keys appear in the UI
- Real-time streaming responses over WebSocket
- JWT-based authentication with 30-day token expiry
- Persistent conversation history (SQLite, Alembic migrations)
- Structured JSON logging (structlog)
- Docker Compose for one-command local setup
- Redis optional — defaults to in-memory store; enable with `REDIS_ENABLED=true`

## Prerequisites

- Docker + Docker Compose, **or**
- Python 3.12+ and Node.js 20+ for local development

---

## Quick Start (Local — no Docker)

```bash
# Backend
cd chatbot/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../env.template ../.env    # edit .env — set at least one API key and SECRET_KEY

# Recommended — handles port cleanup automatically:
./start.sh
# Or manually:
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd chatbot/frontend
npm install
npm start
```

- Frontend: http://localhost:4200
- Backend: http://localhost:8000

## Quick Start (Docker Compose)

```bash
cd chatbot
cp env.template .env          # fill in at least one LLM API key and SECRET_KEY
docker compose up --build
```

- Frontend: http://localhost:4200
- Backend API docs: http://localhost:8000/docs (DEBUG=true only)

---

## Configuration

Copy `chatbot/env.template` to `chatbot/.env` and set:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | JWT signing secret — run `openssl rand -hex 32` | dev placeholder | Yes |
| `LLM_PROVIDER` | Active provider: `anthropic` \| `openai` \| `gemini` \| `aws` | first available | No |
| `ANTHROPIC_API_KEY` | Claude API key | — | At least one key required |
| `OPENAI_API_KEY` | OpenAI API key | — | At least one key required |
| `GOOGLE_API_KEY` | Gemini API key | — | At least one key required |
| `AWS_ACCESS_KEY_ID` | AWS credentials (or use IAM role / `~/.aws/credentials`) | — | At least one key required |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials | — | At least one key required |
| `AWS_REGION` | AWS Bedrock region | `us-east-1` | No |
| `DATABASE_URL` | SQLAlchemy async URL | SQLite at `./data/chatbot.db` | No |
| `REDIS_ENABLED` | Enable Redis for session state | `false` | No |
| `REDIS_URL` | Redis connection URL (when `REDIS_ENABLED=true`) | `redis://localhost:6379/0` | No |
| `DEBUG` | Enables `/docs` and verbose logging | `false` | No |

Only providers with a non-empty API key (or valid AWS credentials) are shown in the model selector.

---

## Deploy to GCP (Cloud Run)

### Prerequisites

- [gcloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated
- Docker installed
- A GCP project with billing enabled

### 1 — One-time setup

```bash
export PROJECT_ID=YOUR_PROJECT_ID
export REGION=asia-southeast1    # change to your preferred region
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
echo -n "your-anthropic-key" | gcloud secrets create ANTHROPIC_API_KEY --data-file=-
echo -n "your-openai-key"    | gcloud secrets create OPENAI_API_KEY    --data-file=-
echo -n "your-google-key"    | gcloud secrets create GOOGLE_API_KEY    --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create SECRET_KEY   --data-file=-
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

# Save the backend URL for the next step
BACKEND_URL=$(gcloud run services describe backend \
  --region=$REGION --format='value(status.url)')
echo "Backend URL: $BACKEND_URL"
```

### 4 — Build and deploy the frontend

```bash
cd ../frontend

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

App is live at `$FRONTEND_URL`.

### Production database (optional but recommended)

Cloud Run is stateless — SQLite data is lost on every redeploy. For persistent storage, use Cloud SQL:

```bash
gcloud sql instances create chatbot-db \
  --database-version=POSTGRES_15 \
  --region=$REGION \
  --tier=db-f1-micro

gcloud sql databases create chatbot --instance=chatbot-db
gcloud sql users create chatbot --instance=chatbot-db --password=YOUR_DB_PASSWORD
```

Then redeploy the backend with:

```bash
--add-cloudsql-instances=${PROJECT_ID}:${REGION}:chatbot-db \
--set-env-vars="DATABASE_URL=postgresql+asyncpg://chatbot:PASSWORD@/chatbot?host=/cloudsql/${PROJECT_ID}:${REGION}:chatbot-db"
```

Add `asyncpg` to `requirements.txt` before rebuilding.

---

## How the three environments work

| Mode | Angular env | WebSocket connects to | Backend target |
|------|------------|----------------------|----------------|
| `ng serve` (local) | `environment.ts` | `ws://localhost:4200` → `proxy.conf.json` | `localhost:8000` |
| Docker Compose | `environment.prod.ts` | `ws://localhost:4200` → nginx | `http://backend:8000` |
| Cloud Run | `environment.prod.ts` | `wss://frontend-url` → nginx | `https://backend-xxx.run.app` |

The frontend automatically resolves the WebSocket URL from `window.location` when no explicit `wsUrl` is configured, so the same Docker image works in both Docker Compose and Cloud Run without rebuilding.

---

## Testing

```bash
# Backend
cd chatbot/backend
source .venv/bin/activate
pytest                        # all tests
pytest --cov=app              # with coverage report
pytest -k test_agent_loop     # single test file

# Frontend
cd chatbot/frontend
ng test                       # unit tests (Karma)
ng test --no-watch --code-coverage  # single run with coverage
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit using conventional commits: `git commit -m 'feat: add feature'`
4. Push and open a Pull Request against `main`
5. Squash merge only — keep history clean

---

## Development Notes

it ships pre-configured agents, skills, slash commands, and MCP server integrations. See `CLAUDE.md` for the full developer workflow and `.claude/skills/` for per-technology coding patterns.
