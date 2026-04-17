#!/usr/bin/env bash
# Stop hook: Check for lessons ready to promote (x3+) and orphaned agent-memory files.
# Prints reminders to stderr. Always exits 0 (never blocks).
set -uo pipefail

# Discard stdin JSON from hook protocol
cat > /dev/null 2>&1 || true

LESSONS_FILE="$CLAUDE_PROJECT_DIR/.claude/rules/lessons.md"
AGENT_MEMORY_DIR="$CLAUDE_PROJECT_DIR/.claude/agent-memory"
reminders=""

# Check 1: lessons.md entries at x3 or higher (ready for promotion)
if [ -f "$LESSONS_FILE" ]; then
    promote_count=$(grep -cE '\[x[3-9][0-9]*\]' "$LESSONS_FILE" 2>/dev/null || true)
    promote_count="${promote_count:-0}"
    if [ "$promote_count" -gt 0 ] 2>/dev/null; then
        reminders="${reminders}  - ${promote_count} lesson(s) at x3+ ready for promotion to rules files\n"
    fi

    # Check total entry count (cap is 15)
    entry_count=$(grep -cE '^\#\# \[' "$LESSONS_FILE" 2>/dev/null || true)
    entry_count="${entry_count:-0}"
    if [ "$entry_count" -ge 12 ] 2>/dev/null; then
        reminders="${reminders}  - lessons.md has ${entry_count}/15 entries — consider pruning stale ones\n"
    fi
fi

# Check 2: orphaned agent-memory files
if [ -d "$AGENT_MEMORY_DIR" ]; then
    memory_files=$(find "$AGENT_MEMORY_DIR" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$memory_files" -gt 0 ]; then
        reminders="${reminders}  - ${memory_files} orphaned agent-memory file(s) in .claude/agent-memory/\n"
    fi
fi

# Print reminders if any
if [ -n "$reminders" ]; then
    echo "" >&2
    echo "📋 LESSONS LIFECYCLE REMINDER" >&2
    echo "Run /promote-lessons to process:" >&2
    printf "%b" "$reminders" >&2
    echo "" >&2
fi

exit 0
