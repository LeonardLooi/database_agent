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

# ── Auto-detect corporate CA cert ──────────────────────────────────────────────
# Place your cert at certs/corp-ca.crt — no env var wrangling needed.
if [ -f "certs/corp-ca.crt" ]; then
    if [ -z "${CORPORATE_CA_CERT}" ]; then
        echo "[build] Corporate CA detected at certs/corp-ca.crt — injecting into build"
        CORPORATE_CA_CERT=$(cat "certs/corp-ca.crt")
        export CORPORATE_CA_CERT
    fi
else
    echo "[build] No corporate CA found at certs/corp-ca.crt — skipping (non-enterprise build)"
fi

# ── Build ───────────────────────────────────────────────────────────────────────
docker-compose up --build -d

echo "[build] Pruning dangling images from previous build..."
docker image prune -f
echo "[build] Done."
