#!/usr/bin/env bash
# UserPromptSubmit: Append every user prompt with ISO 8601 timestamp to blackbox/audit.md.
# Handles auto-creation and monthly rotation. Always exits 0 (never blocks).
set -uo pipefail

input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt // ""' 2>/dev/null) || prompt=""

[ -z "$prompt" ] && exit 0

LOGFILE="$CLAUDE_PROJECT_DIR/blackbox/audit.md"
CURRENT_MONTH=$(date -u +"%Y-%m")

# Auto-create blackbox/audit.md if it doesn't exist
if [ ! -f "$LOGFILE" ]; then
    mkdir -p "$CLAUDE_PROJECT_DIR/blackbox"
    printf "# Blackbox — Prompt Audit Log\n# Append-only. Raw user inputs for session auditability.\n" > "$LOGFILE"
fi

# Log rotation: if first entry month differs from current month, archive and start fresh
FIRST_MONTH=$(grep -m1 "^## [0-9]" "$LOGFILE" | grep -oE "[0-9]{4}-[0-9]{2}" | head -1 || true)
if [ -n "$FIRST_MONTH" ] && [ "$FIRST_MONTH" != "$CURRENT_MONTH" ]; then
    mv "$LOGFILE" "$CLAUDE_PROJECT_DIR/blackbox/audit-${FIRST_MONTH}.md"
    printf "# Blackbox — Prompt Audit Log\n# Append-only. Raw user inputs for session auditability.\n" > "$LOGFILE"
fi

# Append prompt entry
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
{
    printf "\n## %s\n" "$timestamp"
    printf "%s\n" "$prompt"
    printf -- "---\n"
} >> "$LOGFILE" 2>/dev/null || true

exit 0
