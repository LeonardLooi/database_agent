# Cloud Run Anti-Patterns Checklist

Run this checklist before deploying any Cloud Run Function. Every HIGH or CRITICAL item must be resolved.

## Anti-Patterns

| Anti-pattern | Severity | Fix |
|-------------|----------|-----|
| Service account JSON keys in GitHub Secrets or env vars | CRITICAL | Use Workload Identity Federation — no long-lived keys |
| `cloudbuild.yaml` used instead of GitHub Actions | WORKSPACE RULE | Delete cloudbuild.yaml; use `.github/workflows/*.yml` only |
| No `GET /health` endpoint | HIGH | Expose `GET /health` returning HTTP 200 — required for Cloud Run readiness |
| No `SIGTERM` handler | HIGH | Cloud Run sends SIGTERM 10s before SIGKILL. Handle graceful shutdown or in-flight requests are dropped |
| Binding to `localhost` instead of `0.0.0.0` | HIGH | Cloud Run's load balancer cannot reach the container — always bind `0.0.0.0` |
| Hardcoded port (not reading `PORT` env var) | HIGH | Use `process.env.PORT`, `os.environ.get("PORT", 8080)`, or `${PORT:-8080}` |
| Writing large files to `/tmp` | HIGH | `/tmp` is in-memory (tmpfs) — max 512Mi by default. Use Cloud Storage for large objects |
| Long-running background tasks after response returned | HIGH | Cloud Run CPU is throttled after response. Use Cloud Tasks or Pub/Sub for async work |
| CPU-intensive work without `--concurrency=1` | HIGH | Multiple concurrent requests compete for CPU — set `--concurrency 1` or make work async |
| Returning HTTP 200 on processing errors (Pub/Sub) | HIGH | Pub/Sub will not retry — always return 5xx for transient errors you want retried |
| Blocking reactive thread (Spring WebFlux) | HIGH | Never call `.block()` in a WebFlux pipeline — use `Mono.fromCallable` for CPU-bound work |
| Global mutable state across requests (Python) | MEDIUM | FastAPI is multi-threaded — guard shared state with locks or use immutable module-level singletons |
| Missing structured logging (plain print/console.log) | MEDIUM | Use structured JSON logging — Cloud Logging parses structured logs for filtering and alerting |
| No max-instances set | MEDIUM | Unbounded scaling can exhaust Pub/Sub quota or DB connections — always set `--max-instances` |
| node:20 or python:3.11 base images | MEDIUM | Use `node:24-alpine` and `python:3.14-slim` — workspace mandates current runtime versions |
| Running as root in container | MEDIUM | Add non-root user in Dockerfile — see `docker` skill `reference/dockerfiles.md` |
| Secrets in environment variables (plaintext) | MEDIUM | Mount secrets from Secret Manager via `--set-secrets` flag or volume mount |
| No retry budget on Pub/Sub subscription | LOW | Set `--max-delivery-attempts` on subscription to prevent infinite retry loops on poison pills |

---

## SIGTERM Handler Examples

**Python:**
```python
import signal, sys

def handle_sigterm(*_):
    # flush buffers, close DB connections
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
```

**Node.js (NestJS / Fastify):**
```typescript
process.on('SIGTERM', async () => {
  await app.close();   // NestJS: graceful shutdown
  process.exit(0);
});
```

**Java (Spring Boot):**
Spring Boot handles SIGTERM automatically via `@PreDestroy` and `server.shutdown=graceful` in `application.yml`.
```yaml
server:
  shutdown: graceful
spring:
  lifecycle:
    timeout-per-shutdown-phase: 8s  # Stay under Cloud Run's 10s window
```

---

## Pre-Deploy Checklist

- [ ] `GET /health` returns 200
- [ ] Port bound to `0.0.0.0:${PORT}`
- [ ] SIGTERM handler in place
- [ ] No service account JSON keys
- [ ] GitHub Actions workflow (no cloudbuild.yaml)
- [ ] `--max-instances` set
- [ ] Structured logging (no print/console.log)
- [ ] Non-root user in Dockerfile
- [ ] `/tmp` usage reviewed (no large files)
