#!/bin/sh
# Build all services and prune dangling images.
#
# Enterprise setup (one-time only):
#   1. cp enterprise-build.example .env.build
#   2. Fill in HTTP_PROXY / HTTPS_PROXY in .env.build (if your network requires a proxy)
#   3. Drop your corporate CA cert at: certs/corp-ca.crt
#   4. ./build.sh  — cert and proxy are injected automatically, no further config needed
#
# Non-enterprise: just run ./build.sh
set -e

# ── Load proxy settings from .env.build ────────────────────────────────────────
if [ -f ".env.build" ]; then
    echo "[build] Loading proxy settings from .env.build"
    set -a
    # shellcheck source=.env.build.example
    . ./.env.build
    set +a
fi

# ── Pre-copy corporate CA cert into each build context ──────────────────────────
# Avoids shell/env limitations when cert content is large.
# Each Dockerfile uses COPY corp-ca.crt directly — no ARG injection needed.
CERT_SRC="certs/corp-ca.crt"
for ctx in backend frontend nginx; do
    if [ -f "$CERT_SRC" ]; then
        cp "$CERT_SRC" "$ctx/corp-ca.crt"
    else
        # Empty placeholder — Dockerfile checks file size before installing
        : > "$ctx/corp-ca.crt"
    fi
done

if [ -f "$CERT_SRC" ]; then
    echo "[build] Corporate CA detected at $CERT_SRC — copied into build contexts"
else
    echo "[build] No corporate CA found at $CERT_SRC — skipping (non-enterprise build)"
fi

# ── Build ───────────────────────────────────────────────────────────────────────
# Detect compose v2 (docker compose) or v1 (docker-compose)
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
else
    COMPOSE="docker-compose"
fi

$COMPOSE up --build -d

echo "[build] Pruning dangling images from previous build..."
docker image prune -f

# ── Cleanup — remove cert copies from source directories ────────────────────────
for ctx in backend frontend nginx; do
    rm -f "$ctx/corp-ca.crt"
done

echo "[build] Done."
