# Communication Matrix

Every link must be tested with a real request — no mocking, no assumptions.
Mark each CONNECTED ✅ or BROKEN ❌.
A broken link is P0: fix it before computing any health score.

---

## Full matrix

```
Browser
  └──► Nginx :80/:443
         ├──► /          → Angular static files
         └──► /api/*     → FastAPI :8000
                              ├──► PostgreSQL :5432
                              ├──► Redis :6379
                              ├──► LLM API (external HTTPS)
                              └──► Internal background tasks

Angular (running in browser, hosted by Nginx)
  └──► Nginx /api/*  (REST + SSE)
         └──► FastAPI
```

---

## Link 1: Browser → Nginx

**Test:**
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost/
curl -s -o /dev/null -w "%{http_code}" http://localhost/api/health
```
**Assert:** Both return `200`  
**Broken signal:** Nginx not running, port not exposed in docker-compose

---

## Link 2: Nginx → FastAPI (proxy)

**Test:**
```bash
# Tail Nginx access log while hitting /api endpoint
docker exec <nginx> tail -f /var/log/nginx/access.log &
curl -s http://localhost/api/health
```
**Assert:** Nginx log shows request forwarded to upstream, FastAPI returns 200  
**Broken signal:** `502 Bad Gateway` — check:
1. `proxy_pass` URL uses Docker service name, not `localhost`
2. FastAPI container is on the same Docker network as Nginx
3. FastAPI is actually listening on the expected port

**Fix template:**
```nginx
upstream api {
  server api:8000;  # 'api' = docker-compose service name
}
location /api/ {
  proxy_pass http://api/;
  proxy_set_header Host $host;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

---

## Link 3: Angular (hosted) → FastAPI via Nginx — REST

**Test:** Open the hosted Angular app (or use Playwright) and trigger each `HttpClient` call.
```bash
# Using curl to simulate what Angular sends
curl -s -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  http://localhost/api/v1/agent/query \
  -d '{"prompt": "test"}'
```
**Assert:** 200 response, body matches OpenAPI schema  
**Broken signal:** CORS error (missing headers), 401 (auth not forwarded), 404 (base URL mismatch)

**CORS fix template (FastAPI middleware):**
```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Link 4: Angular (hosted) → FastAPI via Nginx — SSE

**Test:**
```bash
# Simulate EventSource behaviour
curl -sN -H "Accept: text/event-stream" \
  http://localhost/api/v1/agent/stream \
  --max-time 10
```
**Assert:** `data:` lines appear in output, stream completes with `event: done` or similar  
**Broken signals:**
- No data flows → `proxy_buffering on` (default) blocking SSE
- Connection drops immediately → missing `keep-alive` or incorrect content-type
- Angular component leaks → missing `EventSource.close()` in `ngOnDestroy`

**Nginx SSE location fix:**
```nginx
location /api/v1/agent/stream {
  proxy_pass http://api/v1/agent/stream;
  proxy_buffering off;
  proxy_cache off;
  proxy_read_timeout 300s;
  proxy_set_header Connection '';
  proxy_http_version 1.1;
  add_header X-Accel-Buffering no;
}
```

**Angular teardown fix:**
```typescript
private eventSource?: EventSource;

ngOnDestroy(): void {
  this.eventSource?.close();
}
```

---

## Link 5: FastAPI → PostgreSQL

**Test:**
```bash
docker exec <api> python -c "
import asyncio, asyncpg, os
async def test():
    conn = await asyncpg.connect(os.environ['DATABASE_URL'])
    result = await conn.fetchval('SELECT 1')
    print('DB OK:', result)
    await conn.close()
asyncio.run(test())
"
```
**Assert:** `DB OK: 1`  
**Broken signals:** Connection refused (DB not started), auth failed (wrong credentials), pool exhaustion

**Pool exhaustion fix (SQLAlchemy async):**
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

---

## Link 6: FastAPI → Redis

**Test:**
```bash
docker exec <api> python -c "
import redis.asyncio as redis, asyncio, os
async def test():
    r = redis.from_url(os.environ['REDIS_URL'])
    await r.set('probe', 'ok', ex=10)
    val = await r.get('probe')
    print('Redis OK:', val)
    await r.aclose()
asyncio.run(test())
"
```
**Assert:** `Redis OK: b'ok'`  
**Broken signals:** Connection refused, wrong host/port in env var

---

## Link 7: FastAPI → LLM API (external)

**Test:**
```bash
docker exec <api> python -c "
import asyncio
from app.services.llm import llm_client  # adjust import path

async def test():
    resp = await llm_client.complete('Say hello in one word.')
    print('LLM OK:', resp[:50])
asyncio.run(test())
"
```
**Assert:** Non-empty response within timeout  
**Broken signals:** API key missing/invalid, timeout (check network egress from Docker), rate limit

**Timeout + retry fix (FastAPI side):**
```python
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def call_llm(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(LLM_ENDPOINT, json={"prompt": prompt})
        response.raise_for_status()
        return response.json()["content"]
```

---

## Link 8: FastAPI internal — background tasks

**Test:**
```bash
# Trigger an endpoint that enqueues a background task, then verify completion
curl -s -X POST http://localhost/api/v1/tasks/enqueue -d '{"job": "test"}'
# Wait 2s, check task status endpoint or DB record
sleep 2
curl -s http://localhost/api/v1/tasks/latest
```
**Assert:** Task status shows `completed`, no error in FastAPI logs  
**Broken signal:** Task silently dropped, unhandled exception in background task (check logs)

---

## Link 9: Docker network isolation

**Test — Angular container must NOT directly reach FastAPI:**
```bash
# Get Angular/Nginx container ID
NGINX_ID=$(docker ps --filter name=nginx -q | head -1)
API_CONTAINER=$(docker inspect <api_container> | jq -r '.[0].NetworkSettings.Networks | keys[0]')
API_IP=$(docker inspect <api_container> | jq -r ".[0].NetworkSettings.Networks.${API_CONTAINER}.IPAddress")

# Nginx container should NOT be on the API-only network
docker exec $NGINX_ID curl -s --max-time 2 http://${API_IP}:8000/health || echo "ISOLATED OK"
```
**Pass:** Connection times out or is refused — Nginx reaches FastAPI only via the shared network through the defined upstream  
**Assert:** DB and Redis containers are on `internal: true` network, not directly host-exposed

**Fix template (docker-compose.yml):**
```yaml
networks:
  frontend:          # Nginx + Angular share this
  backend:           # FastAPI + DB + Redis — internal
    internal: true

services:
  nginx:
    networks: [frontend, backend]  # bridge between the two
  api:
    networks: [backend]
  db:
    networks: [backend]
  redis:
    networks: [backend]
```
