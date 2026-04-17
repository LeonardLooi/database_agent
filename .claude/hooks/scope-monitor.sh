#!/usr/bin/env bash
# PreToolUse → Write|Edit: Scope creep monitor.
# Checks prohibited areas, optional task-scope file, and session file count.
# Exit 0 always (warn-only). Violations are logged and emitted to stderr.
set -uo pipefail

STATE_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/state"
VIOLATIONS_LOG="$STATE_DIR/scope-violations.log"
SCOPE_FILE="$STATE_DIR/current-task-scope.json"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Read tool input JSON from stdin
input=$(cat)
file=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null) || file=""

# Skip if no file path detected
[ -z "$file" ] && exit 0

# Resolve to absolute path for consistent matching
if [[ "$file" != /* ]]; then
  file="${CLAUDE_PROJECT_DIR:-$(pwd)}/$file"
fi

# Helper: log and warn
warn() {
  local msg="$1"
  echo "[scope-monitor] WARNING: $msg" >&2
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  echo "$TIMESTAMP | $msg | file=$file" >> "$VIOLATIONS_LOG" 2>/dev/null || true
}

# ── 1. Prohibited areas ────────────────────────────────────────────────────────
if echo "$file" | grep -qE '(^|/)\.git/'; then
  warn "Write to .git/ directory is prohibited — target: $file"
  exit 0
fi

if echo "$file" | grep -qE '(^|/)node_modules/'; then
  warn "Write to node_modules/ is prohibited — target: $file"
  exit 0
fi

if echo "$file" | grep -qE '(^|/)(dist|build|\.dart_tool)/'; then
  warn "Write to build artifact directory (dist/build/.dart_tool) is prohibited — target: $file"
  exit 0
fi

if echo "$file" | grep -qE '(^|/)\.claude/agent-memory/'; then
  warn "Write to .claude/agent-memory/ is prohibited (orphan prevention) — target: $file"
  exit 0
fi

# ── 2. Task scope check (optional — only if scope file exists) ─────────────────
if [ -f "$SCOPE_FILE" ]; then
  approved=$(jq -r '.approved_files[]?' "$SCOPE_FILE" 2>/dev/null) || approved=""
  if [ -n "$approved" ]; then
    matched=0
    while IFS= read -r approved_file; do
      [ -z "$approved_file" ] && continue
      # Support exact match or prefix match (directory)
      if [[ "$file" == "$approved_file" ]] || [[ "$file" == "$approved_file"* ]]; then
        matched=1
        break
      fi
    done <<< "$approved"
    if [ "$matched" -eq 0 ]; then
      warn "File not in approved task scope — target: $file. Check $SCOPE_FILE for approved_files."
    fi
  fi
fi

# ── 3. Session file count check ────────────────────────────────────────────────
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
if git -C "$PROJECT_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  file_count=$(git -C "$PROJECT_DIR" diff --name-only HEAD 2>/dev/null | wc -l | tr -d ' ') || file_count=0
  if [ "$file_count" -ge 25 ]; then
    warn "STRONG SCOPE WARNING: $file_count files modified this session (threshold: 25). Verify scope before continuing."
  elif [ "$file_count" -ge 15 ]; then
    warn "Scope notice: $file_count files modified this session (threshold: 15). Consider whether all changes are in-scope."
  fi
fi

exit 0
