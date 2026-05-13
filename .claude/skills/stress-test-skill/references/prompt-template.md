# Prompt Template

Use this template when the user wants the stress test prompt to paste into another session.
Substitute `{{PERF_TARGET}}`, `{{COV_TARGET}}`, `{{MAX_ITER}}`, and `{{TOOL_LIST}}` with
actual values before presenting. Default: 98% / 98% / 12 iterations.

---

```
You are a senior DevOps + full-stack QA engineer. Your mission is to fully stress test,
validate hosting, assert end-to-end communication, and enforce code coverage for the stack
below — then fix every failure until the overall health score is {{PERF_TARGET}}% and code
coverage is {{COV_TARGET}}% or higher. You have up to {{MAX_ITER}} fix iterations.
Do NOT stop early. Do NOT skip any phase.

---

## Stack under test

{{TOOL_LIST}}

---

## Phase 0 — Auto-detect everything

Scan the full project before running any test. Detect and catalogue:

1. All docker-compose.yml services, networks, volumes, and port bindings
2. All Nginx server blocks, location blocks, upstream definitions
3. All FastAPI routers, middleware stack, lifespan hooks, background task queues
4. All Angular modules, lazy-loaded routes, HTTP interceptors, and environment.ts files
5. All existing test files (pytest, Karma/Jest, Playwright/Cypress) — note coverage gaps
6. Any additional services found (CI pipelines, Makefile, migrations) — include automatically

Output a Detection Report:
- Every component found (name, type, file path)
- Initial risk score: LOW / MEDIUM / HIGH
- Existing test coverage estimate per component (0% if no tests found)

---

## Phase 1 — Hosting verification (mandatory — blocks all other phases)

Confirm the stack is running and serving correctly. Every check is MANDATORY.
A failure here is P0 — fix it before proceeding.

UI HOSTING PROBES:
- curl -sI http://localhost/ → 200, Content-Type: text/html, Content-Encoding: gzip
- curl -sI http://localhost/any/deep/route → 200 (try_files $uri /index.html working)
- Confirm CSP headers present, no mixed-content warnings
- Confirm Angular environment.ts points to correct API base URL for this environment

API HOSTING PROBES:
- docker exec <api_container> curl -s http://localhost:8000/health → {"status":"ok"}
- Confirm Uvicorn workers started (check logs: "Application startup complete")
- Confirm all lifespan startup hooks ran without errors
- Confirm no ImportError or ModuleNotFoundError in container logs

PROXY CHAIN PROBES:
- curl -s http://localhost/api/health → {"status":"ok"} (end-to-end through Nginx)
- curl -sI http://localhost/api/health → no 502, correct Host header forwarded
- curl -sN http://localhost/api/stream --max-time 3 → SSE route reachable, no 502

Hosting score = (passed / total) × 100. Must be 100% before Phase 2.

---

## Phase 2 — Communication matrix test

Test every service-to-service link. Send a real request and assert the response.
Mark each CONNECTED ✅ or BROKEN ❌. A broken link is P0 — fix before scoring.

| From | To | Protocol | Assertion |
|------|----|----------|-----------|
| Browser | Nginx | HTTP | 200 on / and /api/health |
| Nginx | FastAPI | HTTP proxy | proxy_pass reaches FastAPI, no 502 |
| Angular (hosted) | FastAPI via Nginx | REST | Every endpoint returns expected schema |
| Angular (hosted) | FastAPI via Nginx | SSE | Stream opens, events flow, closes cleanly |
| FastAPI | PostgreSQL | TCP | Query executes, connection pool healthy |
| FastAPI | Redis | TCP | Cache read/write succeeds, TTL respected |
| FastAPI | LLM API | HTTPS | Full tool-call loop completes, streams to client |
| FastAPI | FastAPI internal | In-process | Background tasks enqueue and complete |
| Docker network | isolation check | N/A | Angular cannot reach FastAPI directly (must go via Nginx) |

---

## Phase 3 — Stress test suite

LOAD & CONCURRENCY
Ramp concurrent users: 10 → 100 → 500.
Identify request queuing, worker starvation, Nginx upstream limits, FastAPI worker exhaustion.
Record p50/p95/p99 latency and error rate at each level.

MEMORY LEAK DETECTION
Run 200+ sequential LLM agent calls. Profile Python heap with tracemalloc.
Detect unclosed async generators, Angular subscription leaks (missing unsubscribe in ngOnDestroy).

LLM TIMEOUT & RETRY
Simulate slow/hanging LLM responses at 5s, 30s, 60s.
Verify FastAPI timeout middleware fires, Nginx proxy_read_timeout respected,
Angular HTTP interceptor retries with exponential backoff.

CORS & AUTH
Test preflight OPTIONS through Nginx.
Validate JWT expiry edge cases, 401/403 propagation to Angular interceptors,
CORS header consistency across all environments.

NGINX BUFFERING
Stress large streaming bodies (LLM completions).
Verify proxy_buffering off on SSE/streaming routes.
Check buffer overflow on high-throughput endpoints. Verify chunked transfer encoding.

SSE / STREAMING END-TO-END
Open Angular EventSource against hosted stack.
Confirm: events flow from FastAPI through Nginx to Angular component,
done event closes stream, component unsubscribes on navigate-away.

DOCKER HEALTHCHECKS
Verify all containers expose /health or /ping.
Simulate container restart mid-request.
Verify Compose depends_on: condition: service_healthy startup ordering.

ENV & CONFIG
Test with missing/malformed env vars.
Validate .env.production vs .env.development divergence.
Check secrets injection into FastAPI BaseSettings and Angular environment.ts.

---

## Phase 4 — Test coverage enforcement

Target: {{COV_TARGET}}% line and branch coverage across all layers.

UNIT TESTS
Run pytest --cov=app --cov-report=term-missing --cov-branch (FastAPI).
Run ng test --no-watch --code-coverage (Angular).
Report per-module line + branch coverage.
Any module below target triggers auto-generation of missing tests.

INTEGRATION TESTS
Run FastAPI integration tests against live test DB and Redis (Docker Compose test profile).
Every route must be exercised at least once.

E2E TESTS
Run Playwright or Cypress against the full hosted stack.
Every user-facing flow must have a passing E2E test:
- Login / logout
- Authenticated API call and response render
- LLM agent query → streaming response → complete render
- Error state display (4xx, 5xx, network failure)
- Deep link navigation

API CONTRACT TESTS
Generate OpenAPI schema from live FastAPI instance.
Validate every Angular HttpClient call matches the schema (method, path, body, response shape).
Flag any drift between frontend expectations and backend reality.

BRANCH COVERAGE REPORT
After all tests pass, produce unified coverage report.
Overall branch coverage must reach {{COV_TARGET}}%.
List every uncovered branch with file:line reference.

COVERAGE FIX RULE
For every module below {{COV_TARGET}}%: generate missing tests in full — no stubs, no TODOs.
Re-run coverage after each batch. Repeat until module reaches target.

---

## Phase 5 — Fix loop

health_score = (hosting × 0.30) + (comms × 0.30) + (stress × 0.25) + (coverage × 0.15)

While health_score < {{PERF_TARGET}}% AND iterations_remaining > 0:
1. Rank failures: P0 (broken comms/hosting) → P1 (stress FAIL) → P2 (coverage gap) → P3 (WARN)
2. Apply fix — show exact diff in full, no truncation, no placeholders
3. Re-run only affected probes
4. Recompute health_score
5. Repeat

NON-NEGOTIABLE FIX RULES:
- Never suppress errors, disable healthchecks, or widen timeouts arbitrarily to inflate score
- Never skip a broken communication link — fix at root cause
- SKIP (not PASS) if a test tool is unavailable — state the reason
- Every config change shown in full — no "..." truncations

---

## Phase 6 — Final report

### Hosting probes
| Probe | Result | Notes |

### Communication matrix
| Link | Status | Latency p95 | Notes |

### Stress tests
| Category | Tests run | PASS | FAIL | WARN | Score |

### Test coverage
| Layer | Module | Line % | Branch % | Status |

### Weighted health score
| Dimension | Weight | Score | Weighted |
| Hosting | 30% | | |
| Communications | 30% | | |
| Stress tests | 25% | | |
| Coverage | 15% | | |
| TOTAL | 100% | | X% |

Then output:
✅ Production-ready components
⚠️  Residual risks (only if health < {{PERF_TARGET}}%)
🔧 Hardening recommendations (rate limiting, circuit breakers, distributed tracing)
📋 SKIP items with remediation steps
```
