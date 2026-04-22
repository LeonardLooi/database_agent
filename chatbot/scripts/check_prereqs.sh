#!/usr/bin/env bash
# Verify required tools are installed before starting the stack.
set -euo pipefail

REQUIRED=(docker docker-compose)
MISSING=()

for cmd in "${REQUIRED[@]}"; do
    if ! command -v "$cmd" &>/dev/null; then
        MISSING+=("$cmd")
    fi
done

if ! docker info &>/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not running. Start Docker Desktop and retry."
    exit 1
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "ERROR: Missing required tools: ${MISSING[*]}"
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
fi

CHATBOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -f "$CHATBOT_DIR/.env" ]; then
    echo "WARNING: .env not found. Copy env.template to .env and fill in your API keys."
    echo "  cp $CHATBOT_DIR/env.template $CHATBOT_DIR/.env"
fi

echo "Prerequisites OK."
