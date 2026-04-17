#!/bin/bash
# Hook: Validate JSON/YAML — syntax check after writing structured data files
# Event: PostToolUse (Write|Edit)
#
# Validates .json, .yaml, and .yml files after they are written or edited.
# Reports syntax errors as warnings (never blocks).

set -e

# Read hook input from stdin
INPUT=$(cat)

# Extract the file path that was modified
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

if [[ -z "$FILE_PATH" ]] || [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

# Get file extension
EXT="${FILE_PATH##*.}"

case "$EXT" in
  json)
    # Validate JSON
    if ! jq empty "$FILE_PATH" 2>/dev/null; then
      ERROR=$(jq empty "$FILE_PATH" 2>&1 || true)
      cat <<EOF
{
  "systemMessage": "WARNING: Invalid JSON syntax in $FILE_PATH — $ERROR"
}
EOF
      exit 0
    fi
    ;;

  yaml|yml)
    # Validate YAML — try python, then ruby, then skip
    if command -v python3 &>/dev/null; then
      if ! python3 -c "import yaml; yaml.safe_load(open('$FILE_PATH'))" 2>/dev/null; then
        ERROR=$(python3 -c "import yaml; yaml.safe_load(open('$FILE_PATH'))" 2>&1 || true)
        cat <<EOF
{
  "systemMessage": "WARNING: Invalid YAML syntax in $FILE_PATH — $ERROR"
}
EOF
        exit 0
      fi
    elif command -v ruby &>/dev/null; then
      if ! ruby -e "require 'yaml'; YAML.safe_load(File.read('$FILE_PATH'))" 2>/dev/null; then
        cat <<EOF
{
  "systemMessage": "WARNING: Invalid YAML syntax in $FILE_PATH"
}
EOF
        exit 0
      fi
    fi
    ;;

  *)
    # Not a structured data file — skip
    ;;
esac

exit 0
