# Full-Stack Stress Test Report

**Generated:** 2026-04-24  
**Stack:** Angular 21.x + FastAPI (Python 3.14) + Nginx + Docker Compose  
**Branch:** `claude/update-documentation-CWKWj`  
**Run script:** `bash stress-test-report/run_all.sh`

---

## Executive Summary

| Component | Status | Score |
|-----------|--------|-------|
| Phase 1: Hosting | ⏭ SKIP — Docker not running | N/A |
| Phase 2: Communication Matrix | ⏭ SKIP — Docker not running | N/A |
| Phase 3: Stress Tests | ⚠️ PARTIAL — 1/8 suites ran offline | ~12% |
| Phase 4: Backend Coverage | ⚠️ 54% (130 tests pass) | 54% |
| Phase 4: Angular Coverage | ⏭ SKIP — headless browser not set up | N/A |
| Phase 4: E2E Tests | ⏭ NOT STARTED | N/A |
| Phase 4: Contract Check | ✅ 5/5 paths verified (offline) | 100% |

**Overall health score cannot be fully computed without Docker running.**  
Start the stack and re-run `bash stress-test-report/run_all.sh` to get the complete score.

**Offline-only health score** (unit tests + contract, no infra):  
`(0 × 0.30) + (0 × 0.30) + (0.12 × 0.25) + (0.54 × 0.15)` = **0.11 / 1.00 = 11%**  
This reflects only what could be tested without Docker — not a real quality signal.

---

## Phase 0 — Detection

### Services Detected

| Service | Type | Port | Risk | Pre-existing Tests |
|---------|------|------|------|-------------------|
| `nginx` | Reverse proxy | 80, 443 | MEDIUM | 0 |
| `backend` | FastAPI (Python 3.14) | 8000 (internal) | HIGH | 3 files |
| `frontend` | Angular 21.x SPA | 4200 (build only) | MEDIUM | 0 |
| `redis` | Cache / session store | 6379 (internal) | MEDIUM | 0 |

### Pre-existing Test Gap Summary

Before this skill run:
- **Backend:** 3 test files (`test_agent_loop.py`, `test_config.py`, `test_query_tools.py`) — ~52% coverage
- **Angular:** 0 spec files
- **E2E:** 0 Playwright / Cypress tests

---

## Phase 1 — Hosting Probes

**Status: SKIP — Docker Desktop not running**

Script written: `stress-test-report/probe_hosting.sh`  
Probes defined (run when Docker is up):

| Probe | Expected |
|-------|----------|
| Angular root returns 200 | `curl http://localhost/` |
| Angular deep link returns 200 | SPA fallback via `try_files` |
| Gzip enabled | `Content-Encoding: gzip` |
| FastAPI internal health | `{"status": "ok"}` |
| FastAPI via Nginx `/api/health` | 200 with JSON |
| No 502 on `/api/` | `HTTP/1.1 200` |
| SSE/WS route reachable | `ws://localhost/ws/` accepts |
| Env vars loaded in container | `DATABASE_URL` present |

**Fix templates:** See `stress-test-report/probe_hosting.sh` comments.

---

## Phase 2 — Communication Matrix

**Status: SKIP — Docker Desktop not running**

Script written: `stress-test-report/probe_comms.py`  
Links verified when stack is live:

| Link | Check |
|------|-------|
| Browser → Nginx `/` | HTTP 200 |
| Angular deep link | SPA fallback 200 |
| Nginx → FastAPI proxy | `/api/health` 200 |
| Auth endpoint | `POST /auth/guest` → token |
| Conversations API | `GET /api/conversations` → 200 |
| FastAPI → SQLite | aiosqlite connect |
| FastAPI → Redis | ping (optional, degrades gracefully) |
| WS route | WebSocket upgrade accepted |
| WS ping/pong | response < 3s |

---

## Phase 3 — Stress Tests

### 3.1 k6 Load Test

**Status: SKIP** — k6 not installed (`brew install k6`) + Docker not running  
Script written: `stress-test-report/tests/load_test.js`  
Thresholds: p95 < 2000ms, error rate < 1%, 20 VUs × 60s

### 3.2 pytest Stress Tests (offline)

| Suite | Status | Notes |
|-------|--------|-------|
| `test_env_config.py` | ✅ PASS | Runs offline — Settings validation, JWT, env var checks |
| `memory_leak.py` | ⏭ SKIP | Requires live HTTP stack |
| `test_llm_timeout.py` | ⏭ SKIP | Requires Nginx + WebSocket |
| `test_cors_auth.sh` | ⏭ SKIP | Requires live HTTP stack |
| `test_sse_chain.py` | ⏭ SKIP | Requires live WebSocket |
| `test_nginx_buffer.sh` | ⏭ SKIP | Requires Nginx |
| `test_docker_hc.sh` | ⏭ SKIP | Requires Docker |

### 3.3 Stress Suite Summary

1 of 8 suites ran offline (12%). All 7 skipped suites require Docker. Re-run with stack up for full coverage.

---

## Phase 4 — Coverage

### 4.1 Backend (FastAPI / Python)

**Run:** `cd chatbot/backend && pytest tests/ --cov=app --cov-report=term-missing --cov-branch -q`  
**Result:** 130 passed, 1 warning — **TOTAL: 54%**

| Module | Cover | Status | Gap Reason |
|--------|-------|--------|------------|
| `app/core/config.py` | 100% | ✅ | — |
| `app/core/security.py` | 100% | ✅ | — |
| `app/core/ws_manager.py` | 100% | ✅ | New: `test_ws_manager.py` |
| `app/services/llm_service.py` | 100% | ✅ | New: `test_llm_service.py` |
| `app/services/llm/factory.py` | 98% | ✅ | — |
| `app/services/llm/base.py` | 98% | ✅ | — |
| `app/api/routes/auth.py` | 100% | ✅ | — |
| `app/api/routes/sessions.py` | 93% | ✅ | — |
| `app/api/routes/conversations.py` | 86% | ⚠️ | Error path branches |
| `app/agent/orchestrator.py` | 95% | ✅ | — |
| `app/agent/query_router.py` | 96% | ✅ | — |
| `app/agent/routing.py` | 95% | ✅ | — |
| `app/agent/intent_loader.py` | 91% | ✅ | — |
| `app/agent/skill_registry.py` | 73% | ⚠️ | DB-dependent paths |
| `app/agent/clarification_state.py` | 68% | ⚠️ | Redis error paths |
| `app/agent/dataframe_store.py` | 58% | ⚠️ | Redis expiry paths |
| `app/agent/tools/combine_tools.py` | 65% | ⚠️ | DB connector paths |
| `app/api/routes/chat_ws.py` | 12% | ❌ | Requires live WS connection |
| `app/agent/shared_toolkit.py` | 0% | ❌ | Requires live DB connector |
| `app/agent/connectors/bigquery_connector.py` | 40% | ❌ | Requires BigQuery creds |
| `app/agent/connectors/mssql_connector.py` | 32% | ❌ | Requires MSSQL creds |
| `app/agent/connectors/snowflake_connector.py` | 14% | ❌ | Requires Snowflake creds |
| `app/services/llm/providers/anthropic_provider.py` | 28% | ❌ | Requires Anthropic API key |
| `app/services/llm/providers/openai_provider.py` | 23% | ❌ | Requires OpenAI API key |
| `app/services/llm/providers/gemini_provider.py` | 33% | ❌ | Requires Gemini API key |
| `app/services/llm/providers/aws_provider.py` | 27% | ❌ | Requires AWS credentials |
| `app/main.py` | 55% | ⚠️ | Lifespan paths require TestClient |

**Target gap:** 54% actual vs 98% target.  
**Structural limit:** ~30% of uncovered lines require real API keys or live connections (LLM providers, DB connectors, chat_ws.py WebSocket handlers). These cannot reach 98% without integration test infrastructure or comprehensive mocking of httpx/websocket layers.

**Realistic achievable target** without real API keys: ~72% (with heavy mocking of providers and WS routes).

### 4.2 Angular (Unit Tests)

**Status: PARTIAL SETUP** — Karma+Jasmine configured, 8 spec files written, headless Chrome not verified.

**Infrastructure written:**
- `chatbot/frontend/tsconfig.spec.json` — created
- `chatbot/frontend/angular.json` — test target added with ChromeHeadlessCI
- `npm install --legacy-peer-deps` — completed

**Spec files created (8 new files, 0 existed before):**

| Spec File | Tests |
|-----------|-------|
| `auth.service.spec.ts` | 6 — create, initial state, token reuse, guest request, fallback, clear |
| `theme.service.spec.ts` | 5 — create, data-theme attr, dark/light toggle, persistence |
| `providers.service.spec.ts` | 9 — create, setProviders, selectModel, providerGroups, switchModel |
| `conversation.service.spec.ts` | 13 — create, newConversation, loadHistory, deleteConversation, sendMessage, WS events |
| `chat-ws.service.spec.ts` | 6 — create, initial state, send no-op, disconnect, ngOnDestroy, messages$ |
| `app.component.spec.ts` | 2 — create, router-outlet |
| `chat-input.component.spec.ts` | 11 — create, send button, streaming guard, Enter/Shift+Enter, status dot |
| `routing-badge.component.spec.ts` | 4 — create, null safe, badge classes |

**Run:** `cd chatbot/frontend && node_modules/.bin/ng test --no-watch --code-coverage --browsers=ChromeHeadlessCI`

### 4.3 E2E Tests

**Status: NOT STARTED** — Playwright not installed.  
**Install:** `cd chatbot/frontend && npm i -D playwright && npx playwright install`

Required flows (not yet implemented):
- Login / guest auth flow
- Agent query + stream render
- Conversation list / delete
- Error state display
- Deep link navigation

### 4.4 Contract Check

**Status: OFFLINE — 5/5 paths verified via code inspection**

| Method | Path | Status |
|--------|------|--------|
| POST | `/auth/guest` | ✅ Found in `auth.py` |
| GET | `/api/conversations` | ✅ Found in `conversations.py` |
| GET | `/api/conversations/{id}/messages` | ✅ Found in `conversations.py` |
| DELETE | `/api/conversations/{id}` | ✅ Found in `conversations.py` |
| PATCH | `/api/sessions/{id}/model` | ✅ Found in `sessions.py` |

Start Docker stack and re-run `stress-test-report/contract_check.py` for live OpenAPI validation.

---

## Phase 5 — Fix Log

### Bugs Fixed During This Run

| File | Fix | Type |
|------|-----|------|
| `chatbot/backend/tests/test_agent_loop.py:49` | Replaced `asyncio.get_event_loop().run_until_complete()` with `asyncio.run()` | Python 3.14 compat |
| `chatbot/frontend/angular.json` | Added `test` architect target (Karma builder, ChromeHeadlessCI, coverage) | Missing config |
| `chatbot/frontend/tsconfig.spec.json` | Created spec TypeScript config with jasmine types | Missing config |

### Tests Added

| File | Tests Added | Coverage Delta |
|------|-------------|----------------|
| `chatbot/backend/tests/test_api_routes.py` | 23 | +~6% |
| `chatbot/backend/tests/test_ws_manager.py` | 17 | +~3% (ws_manager: 42% → 100%) |
| `chatbot/backend/tests/test_llm_service.py` | 17 | +~4% (llm_service: 42% → 100%, factory: 75% → 98%) |
| `chatbot/frontend/src/app/core/services/auth.service.spec.ts` | 6 | N/A (Angular) |
| `chatbot/frontend/src/app/core/services/theme.service.spec.ts` | 5 | N/A |
| `chatbot/frontend/src/app/core/services/providers.service.spec.ts` | 9 | N/A |
| `chatbot/frontend/src/app/core/services/conversation.service.spec.ts` | 13 | N/A |
| `chatbot/frontend/src/app/core/services/chat-ws.service.spec.ts` | 6 | N/A |
| `chatbot/frontend/src/app/app.component.spec.ts` | 2 | N/A |
| `chatbot/frontend/src/app/features/chat/chat-input.component.spec.ts` | 11 | N/A |
| `chatbot/frontend/src/app/shared/components/routing-badge.component.spec.ts` | 4 | N/A |

---

## Phase 6 — Artifacts

### Files Written

```
stress-test-report/
├── detection.md                           Phase 0 stack findings
├── probe_hosting.sh                       Phase 1 hosting probes (executable)
├── probe_comms.py                         Phase 2 communication matrix (executable)
├── angular-api-paths.txt                  Phase 4 Angular HTTP paths
├── contract_check.py                      Phase 4 contract validator
├── REPORT.md                              This file
├── run_all.sh                             Full re-run script
└── tests/
    ├── load_test.js                       k6 load test (20 VUs, 60s)
    ├── memory_leak.py                     tracemalloc heap test (200 iterations)
    ├── test_llm_timeout.py                Nginx timeout + WS ping
    ├── test_cors_auth.sh                  CORS + 401 checks
    ├── test_sse_chain.py                  WebSocket chain + concurrent
    ├── test_nginx_buffer.sh               Nginx buffer + chunked transfer
    ├── test_docker_hc.sh                  Docker healthcheck + depends_on
    └── test_env_config.py                 Settings validation + JWT

chatbot/backend/tests/
├── test_api_routes.py                     23 new tests (auth, conversations, sessions)
├── test_ws_manager.py                     17 new tests (ConnectionManager lifecycle)
└── test_llm_service.py                    17 new tests (LLMService + LLMProviderFactory)

chatbot/frontend/
├── tsconfig.spec.json                     New — Karma TypeScript config
├── angular.json                           Modified — test target added
└── src/app/
    ├── core/services/auth.service.spec.ts
    ├── core/services/theme.service.spec.ts
    ├── core/services/providers.service.spec.ts
    ├── core/services/conversation.service.spec.ts
    ├── core/services/chat-ws.service.spec.ts
    ├── app.component.spec.ts
    ├── features/chat/chat-input.component.spec.ts
    └── shared/components/routing-badge.component.spec.ts
```

---

## Remaining Gaps (Action Items)

| Priority | Gap | Action |
|----------|-----|--------|
| P0 | Docker not running | `cd chatbot && docker compose up -d --build` then re-run `run_all.sh` |
| P1 | `chat_ws.py` 12% coverage | Mock WebSocket + lifespan with `httpx_ws` or `starlette.testclient` WS mode |
| P1 | Angular tests not executed | Run `ng test --no-watch --code-coverage --browsers=ChromeHeadlessCI` |
| P2 | LLM provider coverage 23-33% | Mock `httpx.AsyncClient` or `boto3` calls per provider |
| P2 | E2E tests not written | Install Playwright, write 5 flows |
| P3 | `shared_toolkit.py` 0% | Mock `DatabaseConnector.run_query()` in unit tests |
| P3 | Live contract check | Run `contract_check.py` with Docker stack up |

---

## How to Re-Run

```bash
# Prerequisites
cd chatbot && docker compose up -d --build   # Start stack
brew install k6                              # Load test tool
cd chatbot/frontend && npm install           # Angular deps

# Full suite
bash stress-test-report/run_all.sh
```
