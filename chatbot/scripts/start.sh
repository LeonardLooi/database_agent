#!/usr/bin/env bash
# Start all services. Delegates to build.sh for enterprise CA/proxy support.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHATBOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CHATBOT_DIR"

bash "$SCRIPT_DIR/check_prereqs.sh"

echo "Building and starting services..."
bash "$CHATBOT_DIR/build.sh"

echo ""
echo "Stack is up. Open http://localhost in your browser."
echo "Logs: docker-compose logs -f"
echo "Stop: $SCRIPT_DIR/stop.sh"
