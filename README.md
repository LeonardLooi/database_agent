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

- Multi-provider LLM support — switch between Anthropic Claude, OpenAI GPT, Google Gemini, or AWS Bedrock via a single env var
- Real-time streaming responses over WebSocket
- JWT-based authentication with 30-day token expiry
- Persistent conversation history (SQLite, Alembic migrations)
- Structured JSON logging (structlog)
- Docker Compose for one-command local setup

## Prerequisites

- Docker + Docker Compose, **or**
- Python 3.12+ and Node.js 20+ for local development

## Quick Start (Docker)

```bash
cd chatbot
cp env.template .env          # fill in at least one LLM API key and SECRET_KEY
docker compose up --build
```

- Frontend: http://localhost:4200
- Backend API docs: http://localhost:8000/docs (DEBUG=true only)

## Quick Start (Local)

```bash
# Backend
cd chatbot/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../env.template ../.env    # edit .env
option 1 - Recommended: ./start.sh (The start.sh handles killing any previous instance on port 8000 automatically.)
option 2 - Manual: uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd chatbot/frontend
npm install
npm start
```

## Configuration

Copy `chatbot/env.template` to `chatbot/.env` and set:

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `gemini` \| `aws` | `anthropic` |
| `ANTHROPIC_API_KEY` | Claude API key | — |
| `OPENAI_API_KEY` | OpenAI API key | — |
| `GOOGLE_API_KEY` | Gemini API key | — |
| `AWS_REGION` | AWS Bedrock region | `us-east-1` |
| `SECRET_KEY` | JWT signing secret (use `openssl rand -hex 32`) | dev placeholder |
| `DATABASE_URL` | SQLAlchemy async URL | SQLite at `./data/chatbot.db` |
| `DEBUG` | Enables `/docs` and verbose logging | `false` |

## Development Notes

This repository is also a **Claude Code onboarding kit** — it ships pre-configured agents, skills, slash commands, and MCP server integrations. See `CLAUDE.md` for the full developer workflow and `.claude/skills/` for per-technology coding patterns.
