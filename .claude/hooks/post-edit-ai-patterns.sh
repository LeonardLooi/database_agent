#!/usr/bin/env bash
# post-edit-ai-patterns.sh — PostToolUse (Write|Edit)
# Scans newly written/edited files for AI-specific code pathologies.
# Always exits 0 (warn only — never blocks writes).

set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')

# Only scan actual source files (skip binary, lock files, generated files)
if [[ -z "$FILE_PATH" ]]; then exit 0; fi
if [[ ! -f "$FILE_PATH" ]]; then exit 0; fi

EXT="${FILE_PATH##*.}"
case "$EXT" in
  md|json|lock|yaml|yml|txt|png|jpg|svg|ico) exit 0 ;;
esac

WARNINGS=()

# ── 1. Hallucinated / non-existent imports ──────────────────────────────────
# TypeScript: bare require() of unknown local paths that don't exist
if [[ "$EXT" == "ts" || "$EXT" == "js" ]]; then
  while IFS= read -r line; do
    # Detect relative imports where file doesn't exist on disk
    IMPORT_PATH=$(echo "$line" | sed -nE "s/.*from ['\"]([./][^'\"]+)['\"].*/\1/p" | head -1)
    if [[ -n "$IMPORT_PATH" ]]; then
      DIR=$(dirname "$FILE_PATH")
      RESOLVED="$DIR/$IMPORT_PATH"
      # Check without and with extensions
      if [[ ! -f "$RESOLVED" && ! -f "${RESOLVED}.ts" && ! -f "${RESOLVED}.js" && \
            ! -f "${RESOLVED}/index.ts" && ! -f "${RESOLVED}/index.js" ]]; then
        WARNINGS+=("HALLUCINATED_IMPORT: '$IMPORT_PATH' referenced but file not found on disk")
      fi
    fi
  done < <(grep -n "from ['\"]\./" "$FILE_PATH" 2>/dev/null || true)
fi

# ── 2. Placeholder / stub functions ─────────────────────────────────────────
STUB_PATTERNS=(
  'TODO: implement'
  'TODO: add implementation'
  'throw new Error.*not implemented'
  'NotImplementedError'
  'raise NotImplementedError'
  'pass  # TODO'
  '# TODO.*implement'
  'return null; // TODO'
  'return None  # TODO'
  '\.\.\.  # implement'
  'throw Error\("Not implemented"\)'
)
for pattern in "${STUB_PATTERNS[@]}"; do
  MATCHES=$(grep -in "$pattern" "$FILE_PATH" 2>/dev/null | head -3 || true)
  if [[ -n "$MATCHES" ]]; then
    while IFS= read -r match; do
      WARNINGS+=("STUB_FUNCTION: $match")
    done <<< "$MATCHES"
  fi
done

# ── 3. Mock / test fixtures leaking into production code ─────────────────────
MOCK_PATTERNS=(
  'jest\.mock\('
  'sinon\.'
  'unittest\.mock'
  'from unittest.mock import'
  'MockProvider'
  'createMockStore'
  'mockReturnValue'
  'spyOn\('
  '\.mockImplementation\('
  'TestBed\.'
  'fixtures\.'
  'factory_boy'
  'faker\.'
)

# Only warn if file is NOT in a test directory
IS_TEST_FILE=false
if echo "$FILE_PATH" | grep -qiE '(test|spec|__tests__|__mocks__|fixtures)'; then
  IS_TEST_FILE=true
fi

if [[ "$IS_TEST_FILE" == "false" ]]; then
  for pattern in "${MOCK_PATTERNS[@]}"; do
    MATCHES=$(grep -in "$pattern" "$FILE_PATH" 2>/dev/null | head -2 || true)
    if [[ -n "$MATCHES" ]]; then
      while IFS= read -r match; do
        WARNINGS+=("MOCK_LEAK: mock/test code in production file: $match")
      done <<< "$MATCHES"
    fi
  done
fi

# ── 4. Confidence-signalling comments (AI hedging left in code) ───────────────
HEDGE_PATTERNS=(
  '# Note: this may not work'
  '# This might need adjustment'
  '# You may want to change'
  '// Note: this may not work'
  '// This might need adjustment'
  '// You may want to change'
  '# I think'
  '// I think'
  '# Not sure if'
  '// Not sure if'
)
for pattern in "${HEDGE_PATTERNS[@]}"; do
  MATCHES=$(grep -in "$pattern" "$FILE_PATH" 2>/dev/null | head -2 || true)
  if [[ -n "$MATCHES" ]]; then
    while IFS= read -r match; do
      WARNINGS+=("AI_HEDGE_COMMENT: uncertainty comment left in code: $match")
    done <<< "$MATCHES"
  fi
done

# ── 5. Hardcoded placeholder values ──────────────────────────────────────────
PLACEHOLDER_PATTERNS=(
  '"your-api-key-here"'
  '"YOUR_API_KEY"'
  '"REPLACE_ME"'
  '"TODO_FILL_IN"'
  '"changeme"'
  "'changeme'"
  '"placeholder"'
  "'placeholder'"
  '"example.com"'
  'http://localhost:3000.*TODO'
)
for pattern in "${PLACEHOLDER_PATTERNS[@]}"; do
  MATCHES=$(grep -in "$pattern" "$FILE_PATH" 2>/dev/null | head -2 || true)
  if [[ -n "$MATCHES" ]]; then
    while IFS= read -r match; do
      WARNINGS+=("HARDCODED_PLACEHOLDER: $match")
    done <<< "$MATCHES"
  fi
done

# ── Report ────────────────────────────────────────────────────────────────────
if [[ ${#WARNINGS[@]} -gt 0 ]]; then
  LOG_FILE="$CLAUDE_PROJECT_DIR/.claude/ai-patterns-detected.log"
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  {
    echo "[$TIMESTAMP] $FILE_PATH — ${#WARNINGS[@]} AI pattern(s) detected"
    for w in "${WARNINGS[@]}"; do
      echo "  - $w"
    done
  } >> "$LOG_FILE" 2>/dev/null || true

  echo ""
  echo "⚠️  AI PATTERN DETECTOR — $FILE_PATH"
  echo "   ${#WARNINGS[@]} issue(s) found:"
  for w in "${WARNINGS[@]}"; do
    echo "   • $w"
  done
  echo "   Review these before committing."
fi

exit 0
