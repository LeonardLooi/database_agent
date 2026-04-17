#!/bin/bash
# Hook: Notify Completion — desktop notification when Claude stops
# Event: Stop
#
# Sends a desktop notification when a Claude session/task completes.
# Useful for long-running tasks (Ralph loop, agent teams, builds).
#
# Supports: macOS (osascript), Linux (notify-send)
# Disable: set CLAUDE_NOTIFY_DISABLE=1

set -e

# Skip if disabled
if [[ "${CLAUDE_NOTIFY_DISABLE:-0}" == "1" ]]; then
  exit 0
fi

TITLE="Claude Code"
MESSAGE="Task completed"

# Read stop reason from stdin if available
INPUT=$(cat 2>/dev/null || echo "{}")
STOP_REASON=$(echo "$INPUT" | jq -r '.reason // ""' 2>/dev/null || echo "")

if [[ -n "$STOP_REASON" ]]; then
  MESSAGE="$STOP_REASON"
fi

# macOS notification
if [[ "$(uname)" == "Darwin" ]]; then
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\"" 2>/dev/null || true

  # Play completion sound (non-blocking)
  if [[ -f "/System/Library/Sounds/Hero.aiff" ]]; then
    afplay "/System/Library/Sounds/Hero.aiff" &
  fi
  exit 0
fi

# Linux notification
if command -v notify-send &>/dev/null; then
  notify-send "$TITLE" "$MESSAGE" --expire-time=5000 2>/dev/null || true
  exit 0
fi

# Fallback: terminal bell
printf '\a'
exit 0
