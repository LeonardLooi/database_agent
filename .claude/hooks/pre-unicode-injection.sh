#!/bin/bash
# Hook: PreToolUse - Detect invisible Unicode characters used for injection
# Exit 0 = allow, Exit 2 = block
#
# Detects: zero-width chars, RTL/LTR overrides, ANSI escapes,
#          null bytes, tag characters, overlong UTF-8, homoglyphs.
#
# References: CVE-2025-53109/53110 (Unicode sandbox escape)
# Registered in settings.json: PreToolUse matcher "Edit|Write"

set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty')

case "$TOOL_NAME" in
    Edit|Write) ;;
    *) exit 0 ;;
esac

CONTENT=""
case "$TOOL_NAME" in
    Write) CONTENT=$(echo "$TOOL_INPUT" | jq -r '.content // empty') ;;
    Edit)  CONTENT=$(echo "$TOOL_INPUT" | jq -r '.new_string // empty') ;;
esac

[[ -z "$CONTENT" ]] && exit 0

# === ZERO-WIDTH CHARACTERS (U+200B-U+200D, U+FEFF) ===
if echo "$CONTENT" | grep -qP '[\x{200B}-\x{200D}\x{FEFF}]'; then
    echo "BLOCKED: Zero-width characters detected (U+200B-U+200D or BOM). Can hide malicious instructions." >&2
    exit 2
fi

# === BIDIRECTIONAL TEXT OVERRIDE (U+202A-U+202E, U+2066-U+2069) ===
if echo "$CONTENT" | grep -qP '[\x{202A}-\x{202E}\x{2066}-\x{2069}]'; then
    echo "BLOCKED: Bidirectional text override detected. Can disguise malicious commands." >&2
    exit 2
fi

# === ANSI ESCAPE SEQUENCES ===
if echo "$CONTENT" | grep -qE $'\x1b\[|\x1b\]|\x1b\('; then
    echo "BLOCKED: ANSI escape sequence detected. Can manipulate terminal display." >&2
    exit 2
fi

# === NULL BYTES ===
if echo "$CONTENT" | grep -qP '\x00'; then
    echo "BLOCKED: Null byte detected. Can cause string truncation attacks." >&2
    exit 2
fi

# === TAG CHARACTERS (U+E0000-U+E007F) ===
if echo "$CONTENT" | grep -qP '[\x{E0000}-\x{E007F}]'; then
    echo "BLOCKED: Unicode tag characters detected. Can embed invisible data." >&2
    exit 2
fi

# === OVERLONG UTF-8 ===
if echo "$CONTENT" | grep -qP '[\xC0-\xC1][\x80-\xBF]'; then
    echo "BLOCKED: Overlong UTF-8 sequence detected. Can bypass security filters." >&2
    exit 2
fi

# === HOMOGLYPHS (warn only — may be legitimate multilingual content) ===
HOMOGLYPHS_FOUND=false
if echo "$CONTENT" | grep -qP '[\x{0430}\x{0435}\x{043E}\x{0440}\x{0441}\x{0445}]'; then
    HOMOGLYPHS_FOUND=true
fi
if echo "$CONTENT" | grep -qP '[\x{0391}-\x{03C9}]' && echo "$CONTENT" | grep -qP '[a-zA-Z]'; then
    HOMOGLYPHS_FOUND=true
fi
if [[ "$HOMOGLYPHS_FOUND" == "true" ]]; then
    echo '{"systemMessage": "Warning: Potential homoglyph characters detected (Cyrillic/Greek mixed with Latin). Verify this is not a filter bypass attempt."}'
fi

exit 0
