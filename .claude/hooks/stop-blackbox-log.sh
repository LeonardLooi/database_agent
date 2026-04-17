#!/usr/bin/env bash
# Stop hook: Append git-changed files to blackbox/session-log.md as a
# mechanical backup record. Handles auto-creation and monthly rotation.
# Always exits 0 (never blocks).
set -uo pipefail

# Discard stdin JSON from hook protocol
cat > /dev/null 2>&1 || true

LOGFILE="$CLAUDE_PROJECT_DIR/blackbox/session-log.md"
CURRENT_MONTH=$(date -u +"%Y-%m")

# Auto-create blackbox/session-log.md if it doesn't exist
if [ ! -f "$LOGFILE" ]; then
    mkdir -p "$CLAUDE_PROJECT_DIR/blackbox"
    printf "# Blackbox — Session Log\n# Append-only. See .claude/rules/blackbox-policy.md\n" > "$LOGFILE"
fi

# Log rotation: if first entry month differs from current month, archive and start fresh
FIRST_MONTH=$(grep -m1 "^## [0-9]" "$LOGFILE" | grep -oE "[0-9]{4}-[0-9]{2}" | head -1 || true)
if [ -n "$FIRST_MONTH" ] && [ "$FIRST_MONTH" != "$CURRENT_MONTH" ]; then
    mv "$LOGFILE" "$CLAUDE_PROJECT_DIR/blackbox/archive-${FIRST_MONTH}.md"
    printf "# Blackbox — Session Log\n# Append-only. See .claude/rules/blackbox-policy.md\n" > "$LOGFILE"
fi

# Get list of files changed in this session
changed=$(git -C "$CLAUDE_PROJECT_DIR" diff --name-only HEAD 2>/dev/null | head -20 || true)
[ -z "$changed" ] && exit 0

# Append git snapshot entry
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
{
    printf "\n<!-- git-snapshot %s -->\n" "$timestamp"
    echo "$changed" | sed 's/^/- /'
    printf "<!-- end-snapshot -->\n"
} >> "$LOGFILE" 2>/dev/null || true

# Diagram staleness detection: warn if changed files may affect a known diagram.
# Convention: src/auth/ → docs/diagrams/auth-flow.md (folder name = diagram prefix)
DIAGRAMS_DIR="$CLAUDE_PROJECT_DIR/docs/diagrams"
if [ -d "$DIAGRAMS_DIR" ]; then
    stale_warnings=""
    while IFS= read -r diagram_file; do
        # Extract keyword from diagram filename: auth-flow.md → auth
        keyword=$(basename "$diagram_file" .md | cut -d'-' -f1)
        if echo "$changed" | grep -qi "${keyword}/"; then
            rel_path="${diagram_file#$CLAUDE_PROJECT_DIR/}"
            stale_warnings="${stale_warnings}  - ${rel_path} (${keyword}/ was modified)\n"
        fi
    done < <(find "$DIAGRAMS_DIR" -name "*.md" 2>/dev/null)

    if [ -n "$stale_warnings" ]; then
        {
            printf "\n<!-- diagram-staleness %s -->\n" "$timestamp"
            printf "⚠️  Diagrams that may need updating:\n"
            printf "%b" "$stale_warnings"
            printf "<!-- end-diagram-staleness -->\n"
        } >> "$LOGFILE" 2>/dev/null || true
    fi
fi

exit 0
