#!/bin/bash
# PreToolUse hook — blocks raw project-creation commands
# Forces use of scaffold slash commands for all new projects.
#
# How it works:
#   - Reads the Bash tool input JSON from stdin
#   - If the command matches a known project-init pattern, blocks with exit 2
#   - exit 2 = hard block (Claude cannot proceed with this tool call)
#
# Sub-agents cannot invoke slash commands — they are headless.
# The orchestrator (main session) MUST run the scaffold command first
# via: Skill tool → scaffold-<tech>-app <name>

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

block() {
  local matched_cmd="$1"
  local scaffold_cmd="$2"
  local tech="$3"

  cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════╗
║              BLOCKED: Raw Project Creation Detected          ║
╚══════════════════════════════════════════════════════════════╝

  Attempted: $matched_cmd
  Tech:      $tech

  This workspace requires scaffold slash commands for all new projects.
  Sub-agents CANNOT invoke slash commands — they run headlessly.

  ┌─ REQUIRED ACTION ──────────────────────────────────────────┐
  │                                                            │
  │  The ORCHESTRATOR (main session) must run FIRST:           │
  │                                                            │
  │    Skill tool → skill: "$scaffold_cmd"                     │
  │                  args: "<project-name>"                    │
  │                                                            │
  │  Only AFTER the scaffold completes should agents be        │
  │  spawned to add feature code to the existing structure.    │
  │                                                            │
  └────────────────────────────────────────────────────────────┘

  See: .claude/rules/leverage-patterns.md § Orchestrator Pre-Flight

EOF
  exit 2
}

# Flutter
if echo "$COMMAND" | grep -qE '(^|[;&|]\s*)flutter\s+create(\s|$)'; then
  block "flutter create" "scaffold-flutter-app" "Flutter / Dart"
fi

# Angular
if echo "$COMMAND" | grep -qE '(^|[;&|]\s*)ng\s+new(\s|$)'; then
  block "ng new" "scaffold-angular-app" "Angular"
fi

# NestJS
if echo "$COMMAND" | grep -qE '(npx\s+@nestjs/cli\s+new|nest\s+new)(\s|$)'; then
  block "npx @nestjs/cli new / nest new" "scaffold-nestjs-api" "NestJS"
fi

# Python / Django
if echo "$COMMAND" | grep -qE '(^|[;&|]\s*)django-admin\s+startproject(\s|$)'; then
  block "django-admin startproject" "scaffold-python-api" "Python / Django"
fi

# Spring Boot via Spring Initializr CLI or Maven archetype
if echo "$COMMAND" | grep -qE '(spring\s+init|mvn\s+archetype:generate)(\s|$)'; then
  block "spring init / mvn archetype:generate" "scaffold-spring-api" "Java / Spring Boot"
fi

# React Native (no scaffold command yet — warn instead of hard block)
if echo "$COMMAND" | grep -qE '(npx\s+react-native\s+init|npx\s+create-expo-app|npx\s+@react-native-community/cli\s+init)(\s|$)'; then
  cat >&2 <<EOF

⚠️  WARNING: Raw React Native project creation detected.
  Consider loading the mobile-developer skill first for standard structure.
  Proceeding — no scaffold command exists yet for React Native.

EOF
  # exit 0 = allow (warning only)
fi

exit 0
