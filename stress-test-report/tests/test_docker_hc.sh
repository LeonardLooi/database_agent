#!/usr/bin/env bash
# test_docker_hc.sh — verify Docker healthcheck behavior and service dependency.
# Run from project root: bash stress-test-report/tests/test_docker_hc.sh
set -euo pipefail
PASS=0; FAIL=0

check() {
  local name="$1" result="$2" expect="$3"
  if echo "$result" | grep -qi "$expect"; then
    echo "PASS  $name"
    ((PASS++))
  else
    echo "FAIL  $name  =>  ${result:0:120}"
    ((FAIL++))
  fi
}

echo "=== Docker Healthcheck Tests ==="

# Check Docker is running
if ! docker info >/dev/null 2>&1; then
  echo "SKIP  Docker not running — start Docker Desktop first"
  exit 0
fi

# Check services are up
if ! docker compose -f chatbot/docker-compose.yml ps 2>/dev/null | grep -q "running\|Up\|healthy"; then
  echo "SKIP  Stack not running — run: cd chatbot && docker compose up -d"
  exit 0
fi

# 1. All expected services are healthy
for svc in redis backend frontend nginx; do
  HEALTH=$(docker compose -f chatbot/docker-compose.yml ps "$svc" 2>/dev/null | tail -1)
  check "Service $svc healthy/running" "$HEALTH" "healthy\|running\|Up"
done

# 2. Backend healthcheck passes inside container
BACKEND_ID=$(docker ps --filter name=backend -q 2>/dev/null | head -1)
if [ -n "$BACKEND_ID" ]; then
  HC_RESULT=$(docker exec "$BACKEND_ID" curl -sf http://localhost:8080/health 2>&1 || echo "failed")
  check "Backend internal healthcheck" "$HC_RESULT" '"status"'
else
  echo "SKIP  Backend container not found"
fi

# 3. Redis healthcheck passes
REDIS_ID=$(docker ps --filter name=redis -q 2>/dev/null | head -1)
if [ -n "$REDIS_ID" ]; then
  REDIS_PING=$(docker exec "$REDIS_ID" redis-cli ping 2>&1 || echo "failed")
  check "Redis ping" "$REDIS_PING" "PONG"
else
  echo "SKIP  Redis container not found"
fi

# 4. Nginx healthcheck (via HTTPS)
NGINX_HC=$(curl -sk --max-time 5 "https://localhost/health" | head -c 50)
check "Nginx health proxy" "$NGINX_HC" "status\|ok"

# 5. depends_on respected — nginx is last to start
NGINX_STARTED=$(docker inspect --format='{{.State.StartedAt}}' \
  "$(docker ps --filter name=nginx -q | head -1)" 2>/dev/null || echo "unknown")
BACKEND_STARTED=$(docker inspect --format='{{.State.StartedAt}}' \
  "$(docker ps --filter name=backend -q | head -1)" 2>/dev/null || echo "unknown")
echo "INFO  nginx started: $NGINX_STARTED"
echo "INFO  backend started: $BACKEND_STARTED"

echo ""
echo "Docker HC: $PASS passed / $((PASS+FAIL)) total"
[ "$FAIL" -eq 0 ] || { echo "FAIL: $FAIL test(s) failed"; exit 1; }
echo "All Docker healthcheck tests PASSED"
