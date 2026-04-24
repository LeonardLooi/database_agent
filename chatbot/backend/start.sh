#!/usr/bin/env bash
# Start uvicorn from the correct directory and venv, killing any previous
# instance on the target port first.
set -euo pipefail

PORT="${1:-8080}"
APP="app.main:app"

# Always run from the directory this script lives in
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Resolve uvicorn: prefer local venv, fall back to PATH
UVICORN="$SCRIPT_DIR/.venv/bin/uvicorn"
if [ ! -x "$UVICORN" ]; then
  UVICORN="$(command -v uvicorn 2>/dev/null || true)"
fi
if [ -z "$UVICORN" ]; then
  echo "ERROR: uvicorn not found. Activate your venv or install uvicorn." >&2
  exit 1
fi
echo "==> Using uvicorn: $UVICORN"

free_port() {
  local p=$1
  local pids
  pids=$(lsof -ti :"$p" 2>/dev/null || true)
  [ -z "$pids" ] && return 0

  # Kill any uvicorn processes on this port
  local uvicorn_pids=""
  for pid in $pids; do
    if ps -p "$pid" -o command= 2>/dev/null | grep -q "uvicorn"; then
      uvicorn_pids="$uvicorn_pids $pid"
    fi
  done

  if [ -n "$uvicorn_pids" ]; then
    echo "==> Stopping previous uvicorn (PID:$uvicorn_pids)..."
    # shellcheck disable=SC2086
    kill $uvicorn_pids 2>/dev/null || true
    sleep 1
    return 0
  fi

  # Port held by something else — suggest next available port
  echo "ERROR: Port $p is in use by a non-uvicorn process." >&2
  local alt=$((p + 1))
  while lsof -ti :"$alt" &>/dev/null; do
    alt=$((alt + 1))
  done
  echo "  Try:  $0 $alt" >&2
  exit 1
}

echo "==> Checking port $PORT..."
free_port "$PORT"

echo "==> Starting $APP on http://localhost:$PORT"
exec "$UVICORN" "$APP" --reload --host 0.0.0.0 --port "$PORT"
