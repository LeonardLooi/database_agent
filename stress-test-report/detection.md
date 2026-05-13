# Phase 0 — Detection Report
Generated: 2026-04-24

## Stack Overview

| Component | Type | Path | Exposed Port | Risk |
|-----------|------|------|-------------|------|
| nginx | Reverse proxy | `chatbot/nginx/` | 80 (→443), 443 | MEDIUM |
| backend | FastAPI (Python 3.14) | `chatbot/backend/` | internal :8080 | HIGH |
| frontend | Angular 21.x SPA | `chatbot/frontend/` | internal :80 | MEDIUM |
| redis | Cache / session store | Docker image redis:7-alpine | internal :6379 | LOW |
| sqlite | Chat history DB | `chatbot/data/chatbot.db` | none | MEDIUM |

## Docker Services (docker-compose.yml)

- **redis** — redis:7-alpine, internal network `data`, healthcheck: `redis-cli ping`
- **backend** — custom image, port 8080 (internal), depends on redis (healthy)
- **frontend** — custom image, port 80 (internal), depends on backend (healthy)
- **nginx** — custom image, ports 80:80 + 443:443, depends on frontend + backend (healthy)

No extra services detected (Celery, MinIO, Traefik, RabbitMQ, Kafka, Keycloak: none)

## Networks

- `frontend` (bridge) — nginx ↔ frontend
- `app` (bridge) — nginx ↔ backend
- `data` (bridge, internal) — backend ↔ redis (no host access)

## FastAPI Routes

| Method | Path | Router |
|--------|------|--------|
| GET | /health | health.py |
| POST | /auth/guest | auth.py |
| POST | /auth/token | auth.py |
| GET/POST/DELETE | /api/conversations/* | conversations.py |
| GET/DELETE | /api/sessions/* | sessions.py |
| WS | /ws/* | chat_ws.py |

## Nginx Config

- HTTP → HTTPS redirect (301)
- `/api/` → backend (proxy_read_timeout 120s)
- `/auth/` → backend
- `/health` → backend
- `/ws/` → backend (WebSocket, timeout 3600s)
- `/` → frontend (Angular SPA)

## Angular Services & HTTP Paths

| Service | HTTP Paths Used |
|---------|----------------|
| AuthService | POST /auth/guest |
| ConversationService | GET /api/conversations, GET /api/conversations/:id/messages, DELETE /api/conversations/:id |
| ProvidersService | GET /health (providers data), PATCH /api/sessions/* |
| ChatWsService | WS /ws/ |

## Existing Tests

### Backend (chatbot/backend/tests/)
14 test files found:
- test_agent_loop.py, test_auth.py, test_clarification_flow.py
- test_combine_tools.py, test_integration.py, test_intent_clarification_integration.py
- test_intent_loader.py, test_orchestrator.py, test_providers.py
- test_query_router.py, test_routing.py, test_session_model.py
- test_skill_registry.py, test_stress.py

Estimated coverage: UNKNOWN — not yet measured.

### Angular Frontend (chatbot/frontend/src/)
**0 spec files** out of 19 TypeScript source files — CRITICAL GAP

### E2E
No Playwright config, no Cypress config found.

## Runtime Environment

- **Docker**: NOT RUNNING — Phase 1 (hosting probes) cannot execute against live services
- **pytest**: NOT in PATH — .venv/bin/python3 (Python 3.14.4) available at project root
- **Node/Angular CLI**: Not verified yet

## Blockers

| Blocker | Impact | Phases Affected |
|---------|--------|-----------------|
| Docker daemon not running | Cannot probe live services | Phase 1, 2, 3 (hosting/comms/stress) |
| 0 Angular spec files | Coverage gap: 0% frontend | Phase 4 |
| pytest not in PATH | Must use project venv | Phase 4 |
