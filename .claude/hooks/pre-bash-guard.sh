#!/usr/bin/env bash
# PreToolUse → Bash: Block destructive commands before they run.
# Exit 0 = allow, Exit 2 = block (reason sent to Claude via stderr).
set -uo pipefail

# Read the tool input JSON from stdin
input=$(cat)
cmd=$(echo "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || cmd=""

# --- Destructive filesystem commands ---
if echo "$cmd" | grep -qE 'rm\s+-rf\s+/'; then
  echo "BLOCKED: 'rm -rf /' is never allowed." >&2
  exit 2
fi

if echo "$cmd" | grep -qE 'rm\s+-rf\s+\.(\s|$)'; then
  echo "BLOCKED: 'rm -rf .' would delete the entire project. Remove specific paths instead." >&2
  exit 2
fi

# --- Dangerous git commands on main/master ---
if echo "$cmd" | grep -qE 'git\s+push\s+.*(--force|-f)\s.*origin\s+(main|master)|git\s+push\s+(--force|-f)\s+origin\s+(main|master)'; then
  echo "BLOCKED: Force-pushing to main/master is not allowed. Use a feature branch." >&2
  exit 2
fi

if echo "$cmd" | grep -qE 'git\s+reset\s+--hard\s+origin/(main|master)'; then
  echo "BLOCKED: Hard-resetting to origin/main|master discards all local work. Use 'git stash' first." >&2
  exit 2
fi

# --- Destructive database commands ---
if echo "$cmd" | grep -qiE '(DROP\s+DATABASE|DROP\s+SCHEMA|TRUNCATE\s+)'; then
  echo "BLOCKED: Destructive database command detected. Run manually if intentional." >&2
  exit 2
fi

# --- Destructive find commands ---
if echo "$cmd" | grep -qE 'find\s+.*\s+-delete'; then
  echo "BLOCKED: 'find ... -delete' can remove files recursively. Use specific rm commands instead." >&2
  exit 2
fi

# --- Remote code execution via curl/wget piped to shell ---
if echo "$cmd" | grep -qE '(curl|wget)\s+.*\|\s*(bash|sh|zsh|source)'; then
  echo "BLOCKED: Piping downloaded content to a shell is dangerous. Download first, review, then execute." >&2
  exit 2
fi

# All clear
exit 0
