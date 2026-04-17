#!/usr/bin/env bash
# lint-commands.sh — Lint all command .md files in .claude/commands/
# bash 3.2 compatible (macOS)

set -uo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_DIR="$(cd "$SCRIPT_DIR/../commands" && pwd)"
COMMANDS_DIR="$DEFAULT_DIR"
QUIET=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dir)
      COMMANDS_DIR="$2"
      shift 2
      ;;
    --quiet)
      QUIET=1
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Usage: $0 [--dir <path>] [--quiet]" >&2
      exit 1
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Counters and collected data
# ---------------------------------------------------------------------------
passed=0
warned=0
failed=0

# Arrays to collect descriptions for duplicate detection (bash 3.2 compatible)
declare -a desc_values=()
declare -a desc_files=()

# Temporary output buffer per file
# We process all files first, then do duplicate check at the end.
# Store per-file results: "status|relpath|messages..."
declare -a file_results=()

# ---------------------------------------------------------------------------
# Helper: strip leading/trailing whitespace from a string
# ---------------------------------------------------------------------------
trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# ---------------------------------------------------------------------------
# lint_file <abs_path> <rel_path>
# Appends one entry to file_results[].
# Entry format:  STATUS|REL_PATH|MSG1|MSG2|...
#   STATUS: ok | warn | fail
# ---------------------------------------------------------------------------
lint_file() {
  local abs_path="$1"
  local rel_path="$2"

  local status="ok"
  local -a messages=()

  # ---- 1. Read the file ----
  local content
  content="$(cat "$abs_path")"

  # ---- 2. Frontmatter presence check ----
  local first_line
  first_line="$(head -1 "$abs_path")"

  local has_frontmatter=0
  local fm_end_line=0   # line number (1-based) of closing ---
  local description_value=""
  local has_description=0
  local has_allowed_tools=0

  if [[ "$first_line" == "---" ]]; then
    # Find second --- (must be on its own line, after line 1)
    local line_num=0
    while IFS= read -r line; do
      line_num=$((line_num + 1))
      if [[ $line_num -eq 1 ]]; then
        continue  # skip opening ---
      fi
      if [[ "$line" == "---" ]]; then
        fm_end_line=$line_num
        break
      fi
    done < "$abs_path"

    if [[ $fm_end_line -gt 1 ]]; then
      has_frontmatter=1
    else
      # Opening --- exists but no closing ---
      has_frontmatter=0
      messages+=("ERROR: frontmatter opened with --- but never closed")
      status="fail"
    fi
  else
    messages+=("ERROR: missing frontmatter (file must start with ---)")
    status="fail"
  fi

  # ---- 3. Parse frontmatter fields (only if frontmatter found) ----
  if [[ $has_frontmatter -eq 1 ]]; then
    local in_fm=0
    local fm_line=0
    while IFS= read -r line; do
      fm_line=$((fm_line + 1))
      if [[ $fm_line -eq 1 ]]; then
        in_fm=1
        continue
      fi
      if [[ $fm_line -eq $fm_end_line ]]; then
        break
      fi
      if [[ $in_fm -eq 1 ]]; then
        # description:
        if [[ "$line" =~ ^description:[[:space:]]*(.*) ]]; then
          has_description=1
          description_value="$(trim "${BASH_REMATCH[1]}")"
        fi
        # allowed-tools:
        if [[ "$line" =~ ^allowed-tools: ]]; then
          has_allowed_tools=1
        fi
      fi
    done < "$abs_path"

    # description present?
    if [[ $has_description -eq 0 ]]; then
      messages+=("ERROR: missing required field: description")
      status="fail"
    else
      # description length > 20 chars?
      local desc_len=${#description_value}
      if [[ $desc_len -le 20 ]]; then
        messages+=("ERROR: description too short (${desc_len} chars, must be > 20)")
        status="fail"
      else
        # Record for duplicate detection
        desc_values+=("$description_value")
        desc_files+=("$rel_path")
      fi
    fi

    # allowed-tools warning
    if [[ $has_allowed_tools -eq 0 ]]; then
      messages+=("WARN: missing allowed-tools field")
      if [[ "$status" == "ok" ]]; then
        status="warn"
      fi
    fi
  fi

  # ---- 4. Body not empty check ----
  if [[ $has_frontmatter -eq 1 && $fm_end_line -gt 0 ]]; then
    # Extract body: everything after line fm_end_line
    local body
    body="$(tail -n +"$((fm_end_line + 1))" "$abs_path")"
    # Count non-whitespace chars
    local body_nws
    body_nws="$(printf '%s' "$body" | tr -d '[:space:]')"
    local body_len=${#body_nws}
    if [[ $body_len -le 30 ]]; then
      messages+=("ERROR: body too short or empty (${body_len} non-whitespace chars, must be > 30)")
      status="fail"
    fi
  fi

  # ---- 5. Build result entry ----
  # Format: status|rel_path|msg1|msg2|...
  local entry="${status}|${rel_path}"
  for msg in "${messages[@]+"${messages[@]}"}"; do
    entry="${entry}|${msg}"
  done

  file_results+=("$entry")
}

# ---------------------------------------------------------------------------
# Collect all .md files (top-level and one level of subdirectories)
# ---------------------------------------------------------------------------
declare -a md_files_abs=()
declare -a md_files_rel=()

# Top-level .md files
for f in "$COMMANDS_DIR"/*.md; do
  [[ -f "$f" ]] || continue
  md_files_abs+=("$f")
  md_files_rel+=("$(basename "$f")")
done

# Subdirectory .md files (one level deep)
for d in "$COMMANDS_DIR"/*/; do
  [[ -d "$d" ]] || continue
  subdir_name="$(basename "$d")"
  for f in "$d"*.md; do
    [[ -f "$f" ]] || continue
    md_files_abs+=("$f")
    md_files_rel+=("${subdir_name}/$(basename "$f")")
  done
done

# ---------------------------------------------------------------------------
# Lint each file
# ---------------------------------------------------------------------------
for i in "${!md_files_abs[@]}"; do
  lint_file "${md_files_abs[$i]}" "${md_files_rel[$i]}"
done

# ---------------------------------------------------------------------------
# Duplicate description detection
# Append WARN entries to the matching file result.
# ---------------------------------------------------------------------------
declare -a dup_warned_files=()

for i in "${!desc_values[@]}"; do
  for j in "${!desc_values[@]}"; do
    if [[ $i -ge $j ]]; then
      continue
    fi
    if [[ "${desc_values[$i]}" == "${desc_values[$j]}" ]]; then
      # Mark both files as having duplicate description warning
      dup_warned_files+=("${desc_files[$i]}")
      dup_warned_files+=("${desc_files[$j]}")
    fi
  done
done

# Add duplicate warnings to existing result entries
if [[ ${#dup_warned_files[@]} -gt 0 ]]; then
  declare -a new_file_results=()
  for entry in "${file_results[@]}"; do
    IFS='|' read -ra parts <<< "$entry"
    local_status="${parts[0]}"
    local_rel="${parts[1]}"

    # Check if this file is in dup_warned_files
    is_dup=0
    for df in "${dup_warned_files[@]}"; do
      if [[ "$df" == "$local_rel" ]]; then
        is_dup=1
        break
      fi
    done

    if [[ $is_dup -eq 1 ]]; then
      entry="${entry}|WARN: duplicate description value"
      if [[ "$local_status" == "ok" ]]; then
        # Replace status
        entry="warn|${entry#ok|}"
      fi
    fi
    new_file_results+=("$entry")
  done
  file_results=("${new_file_results[@]}")
fi

# ---------------------------------------------------------------------------
# Print results
# ---------------------------------------------------------------------------
for entry in "${file_results[@]}"; do
  IFS='|' read -ra parts <<< "$entry"
  entry_status="${parts[0]}"
  entry_rel="${parts[1]}"

  # messages start at index 2
  case "$entry_status" in
    ok)
      passed=$((passed + 1))
      if [[ $QUIET -eq 0 ]]; then
        printf '✅ %s\n' "$entry_rel"
      fi
      ;;
    warn)
      warned=$((warned + 1))
      printf '⚠️  %s\n' "$entry_rel"
      for idx in "${!parts[@]}"; do
        [[ $idx -lt 2 ]] && continue
        printf '   → %s\n' "${parts[$idx]}"
      done
      ;;
    fail)
      failed=$((failed + 1))
      printf '❌ %s\n' "$entry_rel"
      for idx in "${!parts[@]}"; do
        [[ $idx -lt 2 ]] && continue
        printf '   → %s\n' "${parts[$idx]}"
      done
      ;;
  esac
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "RESULT: ${passed} passed, ${warned} warned, ${failed} failed"

# ---------------------------------------------------------------------------
# Exit code
# ---------------------------------------------------------------------------
if [[ $failed -gt 0 ]]; then
  exit 1
fi
exit 0
