#!/usr/bin/env bash
# Post-edit typecheck: runs tsc --noEmit for TS/TSX files, dart analyze for Dart files.
# Non-blocking (exit 0 always) — reports type errors as warnings via systemMessage.

input=$(cat)
file=$(echo "$input" | jq -r '.tool_input.file_path // .tool_input.path // ""' 2>/dev/null) || file=""

[ -z "$file" ] && exit 0
[ -f "$file" ] || exit 0

# TypeScript / Angular / NestJS
if echo "$file" | grep -qE '\.(ts|tsx)$'; then
  # Find nearest tsconfig.json
  dir=$(dirname "$file")
  tsconfig=""
  while [ "$dir" != "/" ]; do
    if [ -f "$dir/tsconfig.json" ]; then
      tsconfig="$dir/tsconfig.json"
      break
    fi
    dir=$(dirname "$dir")
  done

  if [ -n "$tsconfig" ] && command -v npx >/dev/null 2>&1; then
    project_dir=$(dirname "$tsconfig")
    output=$(cd "$project_dir" && npx tsc --noEmit --pretty false 2>&1 | head -20)
    if [ $? -ne 0 ] && [ -n "$output" ]; then
      # Filter errors to only show those in the edited file
      file_basename=$(basename "$file")
      file_errors=$(echo "$output" | grep -i "$file_basename" | head -5)
      if [ -n "$file_errors" ]; then
        echo '{"systemMessage":"TypeScript type errors in edited file:\n'"$(echo "$file_errors" | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|/\\n/g')"'"}'
        exit 0
      fi
    fi
  fi
fi

# Dart / Flutter
if echo "$file" | grep -qE '\.dart$'; then
  if command -v dart >/dev/null 2>&1; then
    output=$(dart analyze "$file" 2>&1 | head -20)
    error_count=$(echo "$output" | grep -cE '(error|warning)' 2>/dev/null || echo "0")
    if [ "$error_count" -gt 0 ]; then
      errors=$(echo "$output" | grep -E '(error|warning)' | head -5)
      echo '{"systemMessage":"Dart analysis issues in edited file:\n'"$(echo "$errors" | sed 's/"/\\"/g' | tr '\n' '|' | sed 's/|/\\n/g')"'"}'
      exit 0
    fi
  fi
fi

exit 0
