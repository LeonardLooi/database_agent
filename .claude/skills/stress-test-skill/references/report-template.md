# Detection Report Format

Output this at the end of Phase 0.

---

## Detection Report

### Services detected

| Service | Type | Config file | Port | Risk | Existing tests |
|---------|------|-------------|------|------|----------------|
| nginx | Reverse proxy | nginx/nginx.conf | 80, 443 | MEDIUM | None found |
| api | FastAPI | app/main.py | 8000 | HIGH | 12 files, ~40% est. |
| db | PostgreSQL | docker-compose.yml | 5432 | MEDIUM | Via integration tests |
| redis | Redis | docker-compose.yml | 6379 | LOW | None found |
| ... | ... | ... | ... | ... | ... |

### Risk scoring criteria
- **HIGH**: Stateful, externally reachable, or handles auth/LLM calls
- **MEDIUM**: Proxy or cache layer — failure affects all downstream
- **LOW**: Internal-only, simple read operations

### Auto-added services (detected but not in default scope)
List any extra services found (Celery, MinIO, etc.) and confirm they are added to scope.

### Coverage gap summary
| Layer | Files found | Files with tests | Est. coverage |
|-------|------------|-----------------|---------------|
| FastAPI routers | 8 | 5 | ~55% |
| FastAPI services | 12 | 7 | ~48% |
| Angular components | 24 | 10 | ~35% |
| Angular services | 8 | 4 | ~40% |
| E2E flows | 6 required | 2 exist | ~33% |

---

# Final Report Template

Output this at the end of Phase 6.

---

## Final stress test report

**Date:** [timestamp]  
**Stack:** Angular 21 + FastAPI + Docker + Nginx [+ detected additions]  
**Iterations used:** X / [max]

---

### Hosting probes

| Probe | Result | Notes |
|-------|--------|-------|
| Angular root route | ✅ PASS | 200, gzip enabled |
| Angular deep link routing | ✅ PASS | try_files working |
| FastAPI internal health | ✅ PASS | {"status":"ok"} |
| FastAPI via Nginx proxy | ✅ PASS | No 502 |
| SSE route reachable | ✅ PASS | Events flow, buffering off |
| ... | | |

**Hosting score: X / X probes passed = 100%**

---

### Communication matrix

| Link | Status | p95 latency | Notes |
|------|--------|-------------|-------|
| Browser → Nginx | ✅ CONNECTED | 8ms | |
| Nginx → FastAPI proxy | ✅ CONNECTED | 12ms | |
| Angular (hosted) → FastAPI REST | ✅ CONNECTED | 95ms | |
| Angular (hosted) → FastAPI SSE | ✅ CONNECTED | First event: 210ms | |
| FastAPI → PostgreSQL | ✅ CONNECTED | 4ms | Pool size: 10 |
| FastAPI → Redis | ✅ CONNECTED | 1ms | |
| FastAPI → LLM API | ✅ CONNECTED | 1.2s avg | |
| FastAPI background tasks | ✅ CONNECTED | Async, non-blocking | |
| Docker network isolation | ✅ VERIFIED | API not directly reachable | |

**Comms score: X / X links connected**

---

### Stress test results

| Category | Tests | PASS | FAIL | WARN | Score |
|----------|-------|------|------|------|-------|
| Load & concurrency | 6 | 6 | 0 | 0 | 100% |
| Memory leak | 3 | 3 | 0 | 0 | 100% |
| LLM timeout/retry | 4 | 4 | 0 | 0 | 100% |
| CORS & Auth | 5 | 5 | 0 | 0 | 100% |
| Nginx buffering | 3 | 3 | 0 | 0 | 100% |
| SSE end-to-end | 4 | 4 | 0 | 0 | 100% |
| Docker healthchecks | 4 | 4 | 0 | 0 | 100% |
| Env & config | 4 | 4 | 0 | 0 | 100% |

**Stress score: X / X = X%**

---

### Test coverage

| Layer | Module | Line % | Branch % | Status |
|-------|--------|--------|----------|--------|
| FastAPI | routers/agent.py | 98.2% | 96.4% | ✅ |
| FastAPI | services/llm.py | 98.7% | 97.1% | ✅ |
| FastAPI | middleware/auth.py | 99.1% | 98.0% | ✅ |
| Angular | agent.service.ts | 98.0% | 95.8% | ✅ |
| Angular | auth.interceptor.ts | 100% | 100% | ✅ |
| Angular | chat.component.ts | 97.2% | 95.0% | ✅ |
| E2E | All required flows | 100% | N/A | ✅ |
| Contract | API schema drift | 0 violations | N/A | ✅ |

**Coverage score: X%**

---

### Weighted health score

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|---------|
| Hosting | 30% | 100% | 30.0 |
| Communications | 30% | 100% | 30.0 |
| Stress tests | 25% | 100% | 25.0 |
| Coverage | 15% | 98.5% | 14.8 |
| **TOTAL** | **100%** | | **99.8%** |

---

### ✅ Production-ready

- [List every component that passed all probes]

### ⚠️ Residual risks (only if health < target)

- [List remaining issues with severity and recommended timeline]

### 🔧 Recommended hardening

- Rate limiting: Add `slowapi` to FastAPI for per-IP rate limits on agent endpoints
- Circuit breaker: Wrap LLM API calls with `circuitbreaker` library (fail fast on repeated LLM errors)
- Distributed tracing: Add OpenTelemetry to FastAPI + Nginx for request-level visibility
- Alerting: Export `/metrics` (Prometheus format) from FastAPI, wire to Grafana
- Angular error tracking: Add Sentry SDK to catch unhandled errors in production

### 📋 SKIP items (if any)

| Test | Reason | Remediation |
|------|--------|-------------|
| [test name] | [tool not installed / permission denied] | [how to fix] |
