#!/usr/bin/env bash
# Force a full image rebuild and restart (clears Docker layer cache).
set -euo pipefail

CHATBOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CHATBOT_DIR"

bash "$(dirname "$0")/check_prereqs.sh"

echo "Stopping existing containers..."
docker-compose down

echo "Rebuilding images (no cache)..."
docker-compose build --no-cache

echo "Starting services..."
docker-compose up -d

echo ""
echo "Rebuild complete. Open http://localhost in your browser."
