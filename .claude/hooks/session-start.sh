#!/bin/bash
# session-start.sh
# Fires on: startup, resume, /clear, /compact
# Injects session resume protocol as context before first model turn.
# Guarantees core-behaviors.md Rule 9 runs even when conversation context is lost.

set -uo pipefail

CONTENT='## SESSION RESUME PROTOCOL (injected by hook)

Context may have been reset (/clear, /compact, or new session).
BEFORE any other action — run these steps:

1. Run TaskList — check for pending/in_progress tasks
2. Tasks found → present this summary before starting new work:
     ## Session Resumed
     - In-progress: [subject] — last step: [description]
     - Pending (unblocked): [list]
     - Pending (blocked): [list + blockers]
     Continue from [next step]? Or review a previous task first?
3. No tasks → ready for new work

Skill loading (before writing any code):
  Java          → java-spring-api skill
  NestJS        → nestjs-api skill
  Python/FastAPI → python-dev skill
  Agentic AI    → agentic-ai-dev skill
  Angular       → angular-spa skill
  Flutter       → flutter-mobile skill
  Debugging     → systematic-debugging skill
  Completion    → verification-before-completion skill
  (Full table: CLAUDE.md → Code Conventions)

Rules auto-loaded each session from: .claude/rules/'

# Escape content for JSON string (single-pass, no external tools)
s="${CONTENT//\\/\\\\}"
s="${s//\"/\\\"}"
s="${s//$'\n'/\\n}"
s="${s//$'\r'/}"
s="${s//$'\t'/\\t}"

printf '{"additionalContext":"%s"}' "$s"
exit 0
