#!/usr/bin/env bash
# PostToolUse → Write|Edit: Auto-format files after Claude modifies them.
# Detects the file type and runs the appropriate formatter if available.
# Exit 0 always (formatting is best-effort, never blocks).
set -uo pipefail

# Read the tool input JSON from stdin
input=$(cat)
file=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null) || file=""

# Skip if no file path or file doesn't exist
[ -z "$file" ] && exit 0
[ -f "$file" ] || exit 0

# --- TypeScript / JavaScript / Angular / HTML / CSS / SCSS ---
if echo "$file" | grep -qE '\.(ts|tsx|js|jsx|html|css|scss|json)$'; then
  if command -v npx >/dev/null 2>&1; then
    # Use project-local Prettier if installed, otherwise skip
    if [ -f node_modules/.bin/prettier ]; then
      npx prettier --write "$file" 2>/dev/null || true
    fi
  fi
fi

# --- Dart / Flutter ---
if echo "$file" | grep -qE '\.dart$'; then
  if command -v dart >/dev/null 2>&1; then
    dart format "$file" 2>/dev/null || true
  fi
fi

# --- Python ---
if echo "$file" | grep -qE '\.py$'; then
  # Try ruff first (fast), then black as fallback
  if command -v ruff >/dev/null 2>&1; then
    ruff format "$file" 2>/dev/null || true
  elif command -v black >/dev/null 2>&1; then
    black --quiet "$file" 2>/dev/null || true
  fi
fi

# --- Java (Spring uses Google Java Format or spotless via Maven) ---
# Skipped: Java formatting is typically handled by Maven plugins (spotless)
# and running the full Maven formatter on each file edit is too slow.
# Use 'mvn spotless:apply' manually or in CI instead.

exit 0
