#!/usr/bin/env bash
# .claude/scripts/lint-agents.sh
# Usage: lint-agents.sh [--dir <path>] [--quiet]
# Exit 0 = all pass, Exit 1 = failures found

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENTS_DIR="${SCRIPT_DIR}/../agents"
QUIET=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      AGENTS_DIR="$2"
      shift 2
      ;;
    --quiet)
      QUIET=true
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--dir <path>] [--quiet]" >&2
      exit 1
      ;;
  esac
done

AGENTS_DIR="$(cd "$AGENTS_DIR" && pwd)"

VALID_COLORS="green blue red orange yellow purple"
REQUIRED_FIELDS="name description model vibe color emoji"

passed=0
failed=0
# seen_names stored as newline-separated "name:filename" pairs (bash 3 compatible)
seen_names_list=""

# Extract frontmatter: content between first and second '---' line
get_frontmatter() {
  local file="$1"
  awk 'NR==1 && /^---/ { found=1; next }
       found && /^---/ { exit }
       found { print }' "$file"
}

# Extract a field value from frontmatter (handles quoted and unquoted values)
get_field() {
  local frontmatter="$1"
  local field="$2"
  echo "$frontmatter" | grep -E "^${field}:" | head -1 | sed "s/^${field}:[[:space:]]*//" | sed 's/^"//' | sed 's/"$//' | sed "s/^'//" | sed "s/'$//"
}

for agent_file in "$AGENTS_DIR"/*.md; do
  [[ -f "$agent_file" ]] || continue
  filename="$(basename "$agent_file")"
  agent_errors=()

  # ── 1. Verify frontmatter delimiters exist ────────────────────────────────
  delimiter_count=$(grep -c "^---" "$agent_file" 2>/dev/null || true)
  if [[ "$delimiter_count" -lt 2 ]]; then
    agent_errors+=("missing frontmatter delimiters (need at least two '---' lines)")
  fi

  frontmatter="$(get_frontmatter "$agent_file")"

  # ── 2. Required fields ────────────────────────────────────────────────────
  for field in $REQUIRED_FIELDS; do
    value="$(get_field "$frontmatter" "$field")"
    if [[ -z "$value" ]]; then
      agent_errors+=("missing required field: ${field}")
    fi
  done

  # ── 3. tools OR allowed-tools must be present ─────────────────────────────
  if ! echo "$frontmatter" | grep -qE "^tools:" && ! echo "$frontmatter" | grep -qE "^allowed-tools:"; then
    agent_errors+=("missing required field: tools (or allowed-tools)")
  fi

  # ── 4. Valid color value ──────────────────────────────────────────────────
  color_value="$(get_field "$frontmatter" "color")"
  if [[ -n "$color_value" ]]; then
    color_valid=false
    for valid in $VALID_COLORS; do
      if [[ "$color_value" == "$valid" ]]; then
        color_valid=true
        break
      fi
    done
    if [[ "$color_valid" == false ]]; then
      agent_errors+=("invalid color '${color_value}' (valid: ${VALID_COLORS})")
    fi
  fi

  # ── 5. Emoji field must be non-empty ──────────────────────────────────────
  emoji_raw=$(echo "$frontmatter" | grep -E "^emoji:" | head -1 | sed 's/^emoji:[[:space:]]*//')
  emoji_stripped=$(echo "$emoji_raw" | tr -d '"'"'"' ')
  if [[ -z "$emoji_stripped" ]]; then
    agent_errors+=("emoji field is empty or missing an emoji character")
  fi

  # ── 6. Description length > 20 chars ─────────────────────────────────────
  desc_value="$(get_field "$frontmatter" "description")"
  desc_len=${#desc_value}
  if [[ "$desc_len" -le 20 ]]; then
    agent_errors+=("description too short (${desc_len} chars, need > 20)")
  fi

  # ── 7. reviewer/auditor filenames must have ## Success Metrics ────────────
  base_noext="${filename%.md}"
  if echo "$base_noext" | grep -qiE "(reviewer|auditor)"; then
    # Check body (after closing frontmatter ---)
    body=$(awk 'BEGIN{count=0} /^---/{count++; if(count==2){found=1; next}} found{print}' "$agent_file")
    if ! echo "$body" | grep -qE "^## Success Metrics"; then
      agent_errors+=("reviewer/auditor agent missing '## Success Metrics' section in body")
    fi
  fi

  # ── 8. Unique name check ──────────────────────────────────────────────────
  name_value="$(get_field "$frontmatter" "name")"
  if [[ -n "$name_value" ]]; then
    existing_owner=$(echo "$seen_names_list" | grep -E "^${name_value}:" | head -1 | sed "s/^${name_value}://")
    if [[ -n "$existing_owner" ]]; then
      agent_errors+=("duplicate name '${name_value}' (also used by ${existing_owner})")
    else
      seen_names_list="${seen_names_list}${name_value}:${filename}"$'\n'
    fi
  fi

  # ── Report ─────────────────────────────────────────────────────────────────
  if [[ ${#agent_errors[@]} -eq 0 ]]; then
    passed=$((passed + 1))
    if [[ "$QUIET" == false ]]; then
      echo "✅ $filename"
    fi
  else
    failed=$((failed + 1))
    echo "❌ $filename"
    for err in "${agent_errors[@]}"; do
      echo "   → $err"
    done
  fi
done

echo ""
echo "RESULT: ${passed} passed, ${failed} failed"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi
exit 0
