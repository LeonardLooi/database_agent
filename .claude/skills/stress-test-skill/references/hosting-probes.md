# Hosting Probes

All probes are mandatory. Hosting score must be 100% before Phase 2 begins.
A failed probe is P0 — fix and re-probe immediately.

---

## Angular / Nginx (UI hosting)

### Probe 1 — Root route serves Angular app
```bash
curl -sI http://localhost/
```
**Pass:** `HTTP/1.1 200`, `Content-Type: text/html`, body contains `<app-root`  
**Fail signals:** 404, 502, empty body, wrong content-type

### Probe 2 — Deep link routing (SPA fallback)
```bash
curl -sI http://localhost/dashboard/settings
curl -sI http://localhost/agent/chat/123
```
**Pass:** `HTTP/1.1 200` on all deep links (not 404)  
**Fix:** Nginx must have `try_files $uri $uri/ /index.html;` in the Angular location block

### Probe 3 — Gzip compression active
```bash
curl -sI --compressed http://localhost/
```
**Pass:** `Content-Encoding: gzip` in response headers  
**Fix:** Add `gzip on; gzip_types text/html application/javascript text/css;` to Nginx config

### Probe 4 — Static assets served with cache headers
```bash
curl -sI http://localhost/main.js  # adjust for actual hashed filename
```
**Pass:** `Cache-Control: max-age=31536000, immutable` (or similar long TTL)  
**Fix:** Add `location ~* \.(js|css|woff2)$ { expires 1y; add_header Cache-Control "immutable"; }` to Nginx

### Probe 5 — Environment API URL is correct
Inspect the built Angular app's `environment.ts` (or `assets/env.js` if runtime-configured):
```bash
docker exec <nginx_container> grep -r "apiUrl\|API_URL\|baseUrl" /usr/share/nginx/html/
```
**Pass:** API URL matches the actual FastAPI Nginx proxy path (e.g. `/api`)  
**Fail signals:** `localhost:8000` hardcoded (breaks in Docker), wrong environment baked in

### Probe 6 — CSP headers present
```bash
curl -sI http://localhost/ | grep -i "content-security-policy"
```
**Pass:** Header present with at least `default-src 'self'`  
**Warn (not fail):** Missing CSP — add to Nginx `add_header Content-Security-Policy`

---

## FastAPI / Docker (API hosting)

### Probe 7 — FastAPI health endpoint reachable internally
```bash
docker exec $(docker ps --filter name=api -q | head -1) \
  curl -s http://localhost:8000/health
```
**Pass:** `{"status":"ok"}` or similar 200 JSON response  
**Fail signals:** Connection refused (Uvicorn not started), 404 (no /health route)

### Probe 8 — Uvicorn workers started successfully
```bash
docker logs $(docker ps --filter name=api -q | head -1) 2>&1 | \
  grep -E "Application startup complete|Uvicorn running"
```
**Pass:** Log line confirms startup complete  
**Fail signals:** `ImportError`, `ModuleNotFoundError`, `address already in use`

### Probe 9 — Lifespan hooks completed
```bash
docker logs $(docker ps --filter name=api -q | head -1) 2>&1 | \
  grep -E "startup|lifespan|connected|initialized"
```
**Pass:** DB connection pool initialized, Redis connected, LLM client ready  
**Fail signals:** Connection errors to DB/Redis during startup

### Probe 10 — All expected containers are healthy
```bash
docker compose ps
```
**Pass:** All services show `healthy` or `running`. No `Exit` or `Restarting`.  
**Fail signals:** Any container in restart loop or exited state

---

## Nginx → FastAPI proxy chain

### Probe 11 — /api proxy reaches FastAPI
```bash
curl -s http://localhost/api/health
```
**Pass:** Same JSON as Probe 7, no 502/504  
**Fail signals:** 502 Bad Gateway (Nginx can't reach FastAPI — check `proxy_pass` URL and Docker network)

### Probe 12 — Host header correctly forwarded
```bash
curl -s http://localhost/api/debug/headers  # if endpoint exists
# or check FastAPI logs for incoming Host header
```
**Pass:** `Host` header matches original request, `X-Forwarded-For` set  
**Fix:** Add to Nginx location block:
```nginx
proxy_set_header Host $host;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Real-IP $remote_addr;
```

### Probe 13 — SSE route reachable through Nginx
```bash
curl -sN --max-time 5 http://localhost/api/stream 2>&1 | head -20
```
**Pass:** Event data flows (`data:` lines appear), no 502  
**Fix:** SSE location block must have:
```nginx
proxy_buffering off;
proxy_cache off;
proxy_set_header Connection '';
proxy_http_version 1.1;
chunked_transfer_encoding on;
```

---

## Common hosting fixes

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| 404 on deep links | Missing `try_files` | `try_files $uri $uri/ /index.html;` |
| 502 on /api/* | Wrong upstream name or port | Check `proxy_pass http://api:8000;` and Docker network |
| SSE events not flowing | `proxy_buffering on` (default) | Add `proxy_buffering off;` to SSE location |
| API URL wrong in Angular | Env baked incorrectly at build | Use runtime config or rebuild with correct env |
| Container won't start | Port conflict or missing env var | Check `docker compose logs <service>` |
| Gzip not working | Missing `gzip_types` | Add JS/CSS/HTML to `gzip_types` |
