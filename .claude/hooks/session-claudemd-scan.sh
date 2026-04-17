#!/bin/bash
# Hook: SessionStart - Scan CLAUDE.md and .claude/*.md for injection attacks
# Always exits 0 (warns via systemMessage, never blocks session start)
#
# Detects: "ignore previous instructions" patterns, shell command piping,
#          base64 obfuscation, hidden HTML comments, long-line obfuscation,
#          non-ASCII near sensitive keywords.
#
# Registered in settings.json: SessionStart (no matcher needed)

set -euo pipefail

SUSPICIOUS_PATTERNS=(
    "ignore.*previous.*instruction"
    "ignore.*all.*instruction"
    "disregard.*instruction"
    "forget.*instruction"
    "new.*instruction.*follow"
    "curl.*\|.*bash"
    "curl.*\|.*sh"
    "wget.*\|.*bash"
    "wget.*\|.*sh"
    "eval\s*\("
    "base64.*decode"
    "\$\(.*curl"
    "\$\(.*wget"
    "<!--.*ignore"
    "<!--.*instruction"
)

WARNINGS=()

scan_file() {
    local file="$1"
    [[ ! -f "$file" ]] && return 0

    for pattern in "${SUSPICIOUS_PATTERNS[@]}"; do
        if grep -qiE "$pattern" "$file" 2>/dev/null; then
            WARNINGS+=("Suspicious pattern in $file: matches '$pattern'")
        fi
    done

    # Very long lines (>500 chars) may indicate obfuscation
    if awk 'length > 500' "$file" | grep -q .; then
        WARNINGS+=("$file contains very long lines (possible obfuscation)")
    fi

    # Non-ASCII near sensitive keywords
    if LC_ALL=C grep -v $'[\x01-\x7F]' "$file" 2>/dev/null | grep -qiE "instruction|ignore|run|execute"; then
        WARNINGS+=("$file has non-ASCII characters near sensitive keywords")
    fi
}

scan_file "CLAUDE.md"
scan_file ".claude/CLAUDE.md"

if [[ -d ".claude" ]]; then
    for md_file in .claude/*.md; do
        # Skip hookify rule files — they contain regex patterns that trigger false positives
        [[ "$md_file" == .claude/hookify.* ]] && continue
        [[ -f "$md_file" ]] && scan_file "$md_file"
    done
fi

if [[ ${#WARNINGS[@]} -gt 0 ]]; then
    WARNING_TEXT="SECURITY WARNING — Suspicious content in project config:\\n"
    for warning in "${WARNINGS[@]}"; do
        WARNING_TEXT+="  - $warning\\n"
    done
    WARNING_TEXT+="\\nReview these files before proceeding."
    echo "{\"systemMessage\": \"$WARNING_TEXT\"}"
fi

exit 0
