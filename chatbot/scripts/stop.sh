#!/usr/bin/env bash
# Stop all running services without removing volumes.
set -euo pipefail

CHATBOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CHATBOT_DIR"

echo "Stopping services..."
docker-compose down
echo "Services stopped. Data volumes are preserved."
