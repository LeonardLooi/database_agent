#!/usr/bin/env bash
# lint-skills.sh — Lint all SKILL.md files in the skills directory
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SCRIPT_DIR}/../skills"
QUIET=0

# Parse flags
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      SKILLS_DIR="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$SKILLS_DIR" ]]; then
  echo "ERROR: Skills directory not found: $SKILLS_DIR" >&2
  exit 1
fi

# Counters
passed=0
warned=0
failed=0
any_errors=0

# Collect all name values for duplicate detection (bash 3.2 compatible — no associative arrays)
# We'll do two passes: first collect names, then lint
all_names=""
all_name_files=""

# First pass: collect names
while IFS= read -r skill_file; do
  frontmatter=$(awk '/^---/{count++; if(count==2) exit; if(count==1) next} count==1{print}' "$skill_file")
  name_val=$(echo "$frontmatter" | awk '/^name:/{sub(/^name:[[:space:]]*/, ""); print; exit}')
  if [[ -n "$name_val" ]]; then
    all_names="${all_names}${name_val}"$'\n'
    all_name_files="${all_name_files}${name_val}::${skill_file}"$'\n'
  fi
done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

# Second pass: lint each file
while IFS= read -r skill_file; do
  skill_dir_name=$(basename "$(dirname "$skill_file")")/SKILL.md

  # Extract frontmatter (lines between first and second ---)
  frontmatter=$(awk '/^---/{count++; if(count==2) exit; if(count==1) next} count==1{print}' "$skill_file")

  # Extract body (lines after second ---)
  body=$(awk '/^---/{count++; next} count>=2{print}' "$skill_file")

  errors=""
  warnings=""

  # Check required field: name
  name_val=$(echo "$frontmatter" | awk '/^name:/{sub(/^name:[[:space:]]*/, ""); print; exit}')
  if [[ -z "$name_val" ]]; then
    errors="${errors}   → ERROR: missing required field: name\n"
  fi

  # Check required field: description (> 20 chars)
  # Handles both inline and YAML block scalar (> or |) multiline descriptions
  desc_val=$(echo "$frontmatter" | awk '/^description:/{sub(/^description:[[:space:]]*/, ""); print; exit}')
  if [[ -z "$desc_val" ]]; then
    errors="${errors}   → ERROR: missing required field: description\n"
  elif [[ "$desc_val" == ">" || "$desc_val" == "|" ]]; then
    # YAML block scalar — content is on following indented lines; always valid
    :
  elif [[ ${#desc_val} -le 20 ]]; then
    errors="${errors}   → ERROR: description must be > 20 chars (got ${#desc_val})\n"
  fi

  # Check required field: metadata: block
  metadata_line=$(echo "$frontmatter" | awk '/^metadata:/{print; exit}')
  if [[ -z "$metadata_line" ]]; then
    errors="${errors}   → ERROR: missing required field: metadata\n"
  fi

  # Check required field: metadata.triggers (indented triggers: under metadata)
  triggers_line=$(echo "$frontmatter" | awk '/^[[:space:]]+triggers:/{print; exit}')
  if [[ -z "$triggers_line" ]]; then
    errors="${errors}   → ERROR: missing required field: metadata.triggers\n"
  fi

  # Check warning: ## Iron Law section in body (strongly recommended, not required)
  iron_law=$(echo "$body" | grep -c '^## Iron Law' || true)
  if [[ "$iron_law" -eq 0 ]]; then
    warnings="${warnings}   → WARN: missing ## Iron Law section\n"
  fi

  # Check warning: allowed-tools
  allowed_tools=$(echo "$frontmatter" | awk '/^allowed-tools:/{print; exit}')
  if [[ -z "$allowed_tools" ]]; then
    warnings="${warnings}   → WARN: missing allowed-tools field\n"
  fi

  # Check warning: body length > 500 lines
  body_lines=$(echo "$body" | wc -l | tr -d ' ')
  if [[ "$body_lines" -gt 500 ]]; then
    warnings="${warnings}   → WARN: body is ${body_lines} lines (recommended ≤ 500)\n"
  fi

  # Check duplicate name
  if [[ -n "$name_val" ]]; then
    # Count how many files have this name
    dup_count=$(echo "$all_name_files" | grep -c "^${name_val}::" || true)
    if [[ "$dup_count" -gt 1 ]]; then
      # Only report if this is not the first occurrence
      first_file=$(echo "$all_name_files" | grep "^${name_val}::" | head -1 | cut -d':' -f3-)
      if [[ "$skill_file" != "$first_file" ]]; then
        errors="${errors}   → ERROR: duplicate name '${name_val}' (also in $(basename "$(dirname "$first_file")")/SKILL.md)\n"
      fi
    fi
  fi

  # Determine status
  if [[ -n "$errors" ]]; then
    failed=$((failed + 1))
    any_errors=1
    echo "❌ ${skill_dir_name}"
    printf "%b" "$errors"
    if [[ -n "$warnings" ]]; then
      printf "%b" "$warnings"
    fi
  elif [[ -n "$warnings" ]]; then
    warned=$((warned + 1))
    if [[ $QUIET -eq 0 ]]; then
      echo "⚠️  ${skill_dir_name}"
      printf "%b" "$warnings"
    else
      echo "⚠️  ${skill_dir_name}"
      printf "%b" "$warnings"
    fi
  else
    passed=$((passed + 1))
    if [[ $QUIET -eq 0 ]]; then
      echo "✅ ${skill_dir_name}"
    fi
  fi

done < <(find "$SKILLS_DIR" -name "SKILL.md" | sort)

echo ""
echo "RESULT: ${passed} passed, ${warned} warned, ${failed} failed"

if [[ $any_errors -eq 1 ]]; then
  exit 1
fi
exit 0
