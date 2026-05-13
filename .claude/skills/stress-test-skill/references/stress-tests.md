# Stress Test Specifications

For each test: state the exact command, record observed metrics, assign PASS/FAIL/WARN, state root cause on failure.

---

## 1. Load & Concurrency

**Tool:** k6 (preferred) or wrk or locust

**k6 script (save as `load_test.js`):**
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m',  target: 100 },
    { duration: '2m',  target: 500 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],  // 95% under 2s
    http_req_failed:   ['rate<0.01'],   // <1% errors
  },
};

export default function () {
  const res = http.get('http://localhost/api/health');
  check(res, { 'status 200': (r) => r.status === 200 });

  const agentRes = http.post(
    'http://localhost/api/v1/agent/query',
    JSON.stringify({ prompt: 'What is 2+2?' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(agentRes, { 'agent 200': (r) => r.status === 200 });
  sleep(1);
}
```
```bash
k6 run load_test.js
```
**Pass thresholds:** p95 < 2000ms, error rate < 1%  
**Watch for:** 502 surges (Nginx upstream limit), 503 (FastAPI worker pool exhausted), memory climb

---

## 2. Memory Leak Detection

**FastAPI heap profiling:**
```python
# Add to FastAPI app temporarily
import tracemalloc, linecache

@app.get("/debug/memory-snapshot")
async def memory_snapshot():
    tracemalloc.start()
    snapshot = tracemalloc.take_snapshot()
    top = snapshot.statistics("lineno")[:10]
    return {"top": [str(s) for s in top]}
```

**Run 200 sequential agent calls:**
```bash
for i in $(seq 1 200); do
  curl -s -o /dev/null -X POST http://localhost/api/v1/agent/query \
    -H "Content-Type: application/json" \
    -d "{\"prompt\": \"iteration $i\"}"
done
```

**After loop — compare memory:**
```bash
# Call snapshot endpoint before and after
curl -s http://localhost/debug/memory-snapshot | python3 -m json.tool
```
**Pass:** Memory growth < 50MB over 200 calls  
**Angular check:** Open DevTools → Memory tab → take heap snapshot before and after 50 navigations. Look for detached DOM nodes.

---

## 3. LLM Timeout & Retry

**Simulate slow LLM with a mock endpoint:**
```python
# test_timeout_server.py — run alongside tests
from fastapi import FastAPI
import asyncio, uvicorn

app = FastAPI()

@app.post("/slow/{delay}")
async def slow_response(delay: int):
    await asyncio.sleep(delay)
    return {"content": f"responded after {delay}s"}

if __name__ == "__main__":
    uvicorn.run(app, port=9999)
```

**Test at 5s / 30s / 60s:**
```bash
# Point LLM_BASE_URL at mock, then:
time curl -s -X POST http://localhost/api/v1/agent/query \
  -d '{"prompt":"test","_mock_delay":5}' \
  -H "Content-Type: application/json"
```

**Assert:**
- 5s delay: request completes or retries within FastAPI timeout (should succeed)
- 30s delay: FastAPI middleware fires `asyncio.TimeoutError`, returns 504
- 60s delay: Nginx `proxy_read_timeout` fires, returns 504 to client
- All cases: Angular shows user-friendly error, not infinite spinner

**Nginx timeout settings:**
```nginx
proxy_connect_timeout 10s;
proxy_send_timeout    30s;
proxy_read_timeout    120s;  # 120s max for streaming; lower for non-streaming
```

---

## 4. CORS & Auth

**Preflight test:**
```bash
curl -sI -X OPTIONS http://localhost/api/v1/agent/query \
  -H "Origin: http://localhost:4200" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Authorization,Content-Type"
```
**Pass:** `Access-Control-Allow-Origin`, `Access-Control-Allow-Methods`, `Access-Control-Allow-Headers` present in response

**JWT expiry test:**
```bash
# Use a token that expires in 5 seconds, wait 6s, then call API
EXPIRED_TOKEN="<generate with short exp claim>"
sleep 6
curl -sI http://localhost/api/v1/protected \
  -H "Authorization: Bearer $EXPIRED_TOKEN"
```
**Pass:** `401 Unauthorized`, Angular interceptor catches and redirects to login (not infinite loop)

**Missing auth test:**
```bash
curl -sI http://localhost/api/v1/protected
```
**Pass:** `401`, proper WWW-Authenticate header, no stack trace in response body

---

## 5. Nginx Buffering

**Test large streaming response:**
```bash
# Generate a large payload from FastAPI (e.g., 100KB streamed)
curl -sN http://localhost/api/v1/agent/stream-large \
  --max-time 30 | wc -c
```
**Pass:** All bytes received, no truncation, no 502  
**Test for correct SSE headers:**
```bash
curl -sI http://localhost/api/v1/agent/stream | grep -E "Transfer-Encoding|X-Accel-Buffering|Cache-Control"
```
**Pass:** `Transfer-Encoding: chunked`, `X-Accel-Buffering: no`

---

## 6. SSE / Streaming End-to-End

**Full chain test:**
```bash
# Connect and capture first 5 events + done event
curl -sN \
  -H "Accept: text/event-stream" \
  -H "Cache-Control: no-cache" \
  http://localhost/api/v1/agent/stream \
  --max-time 20 \
| head -20
```
**Pass:** `data:` lines appear, `event: done` (or `data: [DONE]`) closes the stream

**Mid-stream disconnect test:**
```bash
# Connect, wait 2s, kill — FastAPI should detect disconnection
curl -sN http://localhost/api/v1/agent/stream &
CURL_PID=$!
sleep 2
kill $CURL_PID
# Check FastAPI logs for "Client disconnected" — not an unhandled exception
sleep 1
docker logs <api> 2>&1 | tail -5
```
**Pass:** Log shows graceful disconnect detection, no traceback

**Angular teardown test (manual or Playwright):**
Navigate to agent chat page → start a stream → navigate away mid-stream  
**Pass:** No "Cannot read properties of undefined" errors in browser console, EventSource closed

---

## 7. Docker Healthchecks

**Verify all containers have healthchecks:**
```bash
docker compose config | grep -A5 "healthcheck"
```
**Pass:** Every service has a `healthcheck` block

**Required healthcheck in docker-compose.yml:**
```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 5s
      retries: 3
```

**Restart simulation:**
```bash
docker compose restart api
sleep 5
curl -s http://localhost/api/health
```
**Pass:** Health endpoint returns 200 within `start_period` after restart

**Startup ordering:**
```bash
docker compose config | grep -A3 "depends_on"
```
**Pass:** API depends on DB and Redis with `condition: service_healthy`

---

## 8. Env & Config

**Missing env var test:**
```bash
# Start API with a required var removed
docker run --env-file .env.test \
  -e DATABASE_URL="" \
  your-api-image python -c "from app.config import settings; print(settings)"
```
**Pass:** `ValidationError` from Pydantic (not silent None), container exits with non-zero code

**Env divergence check:**
```bash
diff \
  <(grep -v '^#' .env.production | sort) \
  <(grep -v '^#' .env.development | sort) | grep "^[<>]"
```
**Pass:** Only expected differences (API URLs, debug flags). No missing keys in production.

**Secrets not in image:**
```bash
docker history your-api-image --no-trunc | grep -iE "password|secret|key|token"
```
**Pass:** No secrets baked into image layers
