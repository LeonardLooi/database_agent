#!/usr/bin/env bash
# run_all.sh — re-run the complete stress test suite at any time.
# Run from project root: bash stress-test-report/run_all.sh
#
# Prerequisites:
#   - Docker running + stack up: cd chatbot && docker compose up -d --build
#   - .venv active or use the venv path below
#   - k6 installed: brew install k6 (Phase 3 load test)
#   - playwright installed: npm i -D playwright && npx playwright install (E2E)
set -euo pipefail

VENV_PYTHON="/Users/leonardlooi/Documents/Database_Agent/.venv/bin/python3"
VENV_PYTEST="/Users/leonardlooi/Documents/Database_Agent/.venv/bin/pytest"
BACKEND_DIR="chatbot/backend"
FRONTEND_DIR="chatbot/frontend"

echo ""
echo "╔════════════════════════════════════════════════════╗"
echo "║         Full-Stack Stress Test Suite               ║"
echo "╚════════════════════════════════════════════════════╝"
echo ""

# ── Phase 1: Hosting ─────────────────────────────────────────────────────────
echo "=== Phase 1: Hosting Probes ==="
if docker info >/dev/null 2>&1; then
  bash stress-test-report/probe_hosting.sh
else
  echo "SKIP  Docker not running — start Docker Desktop and re-run"
fi
echo ""

# ── Phase 2: Communication matrix ────────────────────────────────────────────
echo "=== Phase 2: Communication Matrix ==="
if docker info >/dev/null 2>&1; then
  $VENV_PYTHON stress-test-report/probe_comms.py
else
  echo "SKIP  Docker not running"
fi
echo ""

# ── Phase 3: Stress tests ─────────────────────────────────────────────────────
echo "=== Phase 3: Stress Tests ==="

if command -v k6 >/dev/null 2>&1; then
  echo "--- k6 Load Test ---"
  k6 run stress-test-report/tests/load_test.js
else
  echo "SKIP  k6 not installed (brew install k6)"
fi

echo "--- pytest Stress Tests ---"
cd "$BACKEND_DIR" && $VENV_PYTEST \
  ../../stress-test-report/tests/test_env_config.py \
  -v --tb=short
cd - >/dev/null

if docker info >/dev/null 2>&1; then
  echo "--- Memory Leak Test (requires live stack) ---"
  cd "$BACKEND_DIR" && $VENV_PYTEST \
    ../../stress-test-report/tests/memory_leak.py \
    -v --tb=short
  cd - >/dev/null

  echo "--- LLM Timeout Test ---"
  cd "$BACKEND_DIR" && $VENV_PYTEST \
    ../../stress-test-report/tests/test_llm_timeout.py \
    -v --tb=short
  cd - >/dev/null

  echo "--- WS Chain Test ---"
  cd "$BACKEND_DIR" && $VENV_PYTEST \
    ../../stress-test-report/tests/test_sse_chain.py \
    -v --tb=short
  cd - >/dev/null

  echo "--- CORS/Auth Test ---"
  bash stress-test-report/tests/test_cors_auth.sh

  echo "--- Nginx Buffer Test ---"
  bash stress-test-report/tests/test_nginx_buffer.sh

  echo "--- Docker Healthcheck Test ---"
  bash stress-test-report/tests/test_docker_hc.sh
else
  echo "SKIP  Live-stack tests (Docker not running)"
fi
echo ""

# ── Phase 4: Backend coverage ─────────────────────────────────────────────────
echo "=== Phase 4: Backend Coverage ==="
cd "$BACKEND_DIR" && $VENV_PYTEST \
  tests/ \
  --cov=app \
  --cov-report=term-missing \
  --cov-branch \
  -q --no-header
cd - >/dev/null
echo ""

# ── Phase 4: Angular coverage ─────────────────────────────────────────────────
echo "=== Phase 4: Angular Coverage ==="
if command -v ng >/dev/null 2>&1 || [ -f "$FRONTEND_DIR/node_modules/.bin/ng" ]; then
  cd "$FRONTEND_DIR" && node_modules/.bin/ng test \
    --no-watch \
    --code-coverage \
    --browsers=ChromeHeadless 2>&1 || echo "WARN  Angular tests had failures — check output above"
  cd - >/dev/null
else
  echo "SKIP  Angular CLI not found (run: cd chatbot/frontend && npm install)"
fi
echo ""

# ── Phase 4: E2E ──────────────────────────────────────────────────────────────
echo "=== Phase 4: E2E Tests ==="
if command -v npx >/dev/null 2>&1 && [ -f "$FRONTEND_DIR/node_modules/.bin/playwright" ] 2>/dev/null; then
  cd "$FRONTEND_DIR" && npx playwright test --reporter=html
  cd - >/dev/null
else
  echo "SKIP  Playwright not installed (cd chatbot/frontend && npm i -D playwright && npx playwright install)"
fi
echo ""

# ── Phase 4: Contract check ───────────────────────────────────────────────────
echo "=== Phase 4: Contract Check ==="
$VENV_PYTHON stress-test-report/contract_check.py
echo ""

echo "╔════════════════════════════════════════════════════╗"
echo "║  Suite complete — see stress-test-report/REPORT.md ║"
echo "╚════════════════════════════════════════════════════╝"
