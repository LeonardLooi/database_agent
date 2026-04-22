#!/usr/bin/env bash
# Start all services (build images if needed).
set -euo pipefail

CHATBOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$CHATBOT_DIR"

bash "$(dirname "$0")/check_prereqs.sh"

echo "Building and starting services..."
docker-compose up --build -d

echo ""
echo "Stack is up. Open http://localhost in your browser."
echo "Logs: docker-compose logs -f"
echo "Stop: $(dirname "$0")/stop.sh"
