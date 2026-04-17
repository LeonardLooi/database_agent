#!/usr/bin/env bash
# UserPromptSubmit: Behavioral coaching hook — detects intent and suggests the right
# command or agent before Claude responds. 3-tier priority:
#   Tier 0 — Enforcement gates (exit 2: block + redirect)
#   Tier 1 — Discovery suggestions (tool exists, user may not know it)
#   Tier 2 — Contextual nudges (user knows what they want, better path exists)
#
# Dedup guard: never suggests a command already present in the prompt.
# Logs all suggestions to .claude/smart-suggest.jsonl for ROI measurement.
# Always exits 0 unless Tier 0 enforcement fires (exit 2).
set -uo pipefail

input=$(cat)
prompt=$(echo "$input" | jq -r '.prompt // ""' 2>/dev/null) || prompt=""

[ -z "$prompt" ] && exit 0

# Lowercase copy for case-insensitive matching
p=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

LOGFILE="$CLAUDE_PROJECT_DIR/.claude/smart-suggest.jsonl"
timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# Log a suggestion event to JSONL (never fails — errors suppressed)
log_suggestion() {
  local tier="$1" suggested="$2" acted_on="$3" blocked="${4:-false}"
  printf '{"ts":"%s","tier":%s,"suggested":"%s","acted_on":%s,"blocked":%s,"prompt_snippet":"%s"}\n' \
    "$timestamp" "$tier" "$suggested" "$acted_on" "$blocked" \
    "$(echo "$prompt" | head -c 80 | tr '"' "'" | tr '\n' ' ')" \
    >> "$LOGFILE" 2>/dev/null || true
}

# Check if a command/agent is already present in the prompt (dedup guard)
already_present() {
  local cmd="$1"
  echo "$p" | grep -qF "$cmd"
}

# ─────────────────────────────────────────────────────────────────────────────
# TIER 0 — Enforcement gates (hard block, exit 2)
# These represent policy violations. Claude should never see these prompts
# without a redirect. User sees the stderr message immediately.
# ─────────────────────────────────────────────────────────────────────────────

# Block direct push to main/master
if echo "$p" | grep -qE 'push.*(to )?(main|master)|direct.*push|force.?push|--force'; then
  log_suggestion "0" "create-pr" "false" "true"
  echo "⛔  BLOCKED: Direct or force push to main/master is not allowed in this workspace." >&2
  echo "   Use /create-pr to open a pull request instead." >&2
  echo "   Policy: CLAUDE.md §Git Workflow — 'Always create PR — no direct push to develop'" >&2
  exit 2
fi

# Block deleting .env files or secrets
if echo "$p" | grep -qE '(delete|remove|rm).*(\.env|secrets|credentials|\.pem|\.key)'; then
  log_suggestion "0" "null" "false" "true"
  echo "⛔  BLOCKED: Deleting secret/credential files requires explicit human action." >&2
  echo "   Run this command yourself in a terminal if intentional." >&2
  exit 2
fi

# ─────────────────────────────────────────────────────────────────────────────
# TIER 1 — Discovery suggestions (user may not know the tool exists)
# Exit 0 with stdout message — Claude sees prompt + suggestion as additionalContext
# ─────────────────────────────────────────────────────────────────────────────

# Debugging intent → /debug + systematic-debugging skill
if echo "$p" | grep -qE '\b(bug|error|crash|broken|failing|not working|exception|traceback|null pointer|undefined|why (is|does|isn'\''t|doesn'\''t))\b'; then
  if ! already_present "/debug"; then
    log_suggestion "1" "/debug" "false" "false"
    echo "💡 [smart-suggest] Debugging intent detected — consider using /debug which loads the systematic-debugging skill (root-cause-first investigation before any fixes)."
  fi
  exit 0
fi

# Code review intent → tech-specific reviewer agent
if echo "$p" | grep -qE '\b(review|check|audit|look at|is this (right|correct|good)|does this look)\b'; then
  if echo "$p" | grep -qE '\b(flutter|dart|riverpod)\b'; then
    if ! already_present "riverpod-reviewer" && ! already_present "/review"; then
      log_suggestion "1" "riverpod-reviewer" "false" "false"
      echo "💡 [smart-suggest] Flutter/Riverpod review detected — consider dispatching @riverpod-reviewer for provider types, AsyncValue handling, and lifecycle correctness."
    fi
  elif echo "$p" | grep -qE '\b(nestjs|nest|prisma|fastify)\b'; then
    if ! already_present "nestjs-reviewer" && ! already_present "/review"; then
      log_suggestion "1" "nestjs-reviewer" "false" "false"
      echo "💡 [smart-suggest] NestJS review detected — consider dispatching @nestjs-reviewer for module correctness, Prisma usage, and security patterns."
    fi
  elif echo "$p" | grep -qE '\b(spring|java|webflux|reactive)\b'; then
    if ! already_present "spring-reactive-reviewer" && ! already_present "/review"; then
      log_suggestion "1" "spring-reactive-reviewer" "false" "false"
      echo "💡 [smart-suggest] Spring Boot review detected — consider dispatching @spring-reactive-reviewer for reactive correctness and Resilience4j patterns."
    fi
  elif echo "$p" | grep -qE '\b(angular|component|service|directive|standalone)\b'; then
    if ! already_present "ui-standards-expert" && ! already_present "/review"; then
      log_suggestion "1" "ui-standards-expert" "false" "false"
      echo "💡 [smart-suggest] Angular review detected — consider dispatching @ui-standards-expert for design token usage, accessibility, and responsive layout."
    fi
  elif echo "$p" | grep -qE '\b(python|fastapi|pydantic|sqlalchemy)\b'; then
    if ! already_present "code-reviewer" && ! already_present "/review"; then
      log_suggestion "1" "code-reviewer" "false" "false"
      echo "💡 [smart-suggest] Python review detected — consider dispatching @code-reviewer or @silent-failure-hunter for error handling gaps."
    fi
  else
    if ! already_present "/review-code" && ! already_present "/review-pr"; then
      log_suggestion "1" "/review-code" "false" "false"
      echo "💡 [smart-suggest] Review intent detected — consider /review-code or /review-pr for structured multi-role review."
    fi
  fi
  exit 0
fi

# Security concern → security-reviewer agent
if echo "$p" | grep -qE '\b(security|vulnerability|vuln|xss|sql injection|auth|authentication|authorization|jwt|token|password|hash|encrypt|owasp)\b'; then
  if ! already_present "security-reviewer" && ! already_present "/audit-security"; then
    log_suggestion "1" "security-reviewer" "false" "false"
    echo "💡 [smart-suggest] Security intent detected — consider dispatching @security-reviewer or running /audit-security for OWASP Top 10 coverage."
  fi
  exit 0
fi

# Database schema or migration → postgresql-database-reviewer
if echo "$p" | grep -qE '\b(migration|schema|table|index|foreign key|constraint|flyway|prisma migrate|alembic|database design)\b'; then
  if ! already_present "postgresql-database-reviewer" && ! already_present "/design-database"; then
    log_suggestion "1" "postgresql-database-reviewer" "false" "false"
    echo "💡 [smart-suggest] Database change detected — consider dispatching @postgresql-database-reviewer before applying, or /design-database for new schema work."
  fi
  exit 0
fi

# Architecture decision → architect agent or /design-architecture
if echo "$p" | grep -qE '\b(architecture|design the system|system design|how should (we|i) structure|microservice|monolith|api contract|adr|decision record)\b'; then
  if ! already_present "architect" && ! already_present "/design-architecture"; then
    log_suggestion "1" "/design-architecture" "false" "false"
    echo "💡 [smart-suggest] Architecture intent detected — consider /design-architecture or dispatching @architect for C4 diagrams, API contracts, and ADR generation."
  fi
  exit 0
fi

# Explore options / tradeoffs → /brainstorm
if echo "$p" | grep -qE '\b(what (if|are the|would|should)|options|alternatives|explore|compare|which (approach|is better|should (we|i) use)|pros and cons|tradeoff)\b'; then
  if ! already_present "/brainstorm"; then
    log_suggestion "1" "/brainstorm" "false" "false"
    echo "💡 [smart-suggest] Exploration intent detected — consider /brainstorm for ≥3 options with trade-offs and a Mermaid diagram before writing any code."
  fi
  exit 0
fi

# PR creation → /create-pr
if echo "$p" | grep -qE '\b(create (a |the )?pr|open (a |the )?pull request|make (a |the )?pr|submit (a |the )?pr)\b'; then
  if ! already_present "/create-pr"; then
    log_suggestion "1" "/create-pr" "false" "false"
    echo "💡 [smart-suggest] PR creation intent detected — /create-pr embeds a risk score, conventional title, and test plan automatically."
  fi
  exit 0
fi

# Deploy / ship → /ship
if echo "$p" | grep -qE '\b(deploy|ship|release|production|ready to merge|go live)\b'; then
  if ! already_present "/ship"; then
    log_suggestion "1" "/ship" "false" "false"
    echo "💡 [smart-suggest] Deploy intent detected — /ship runs the full pre-deploy gate (tests, security audit, design system lint, dependency CVE scan) before merge."
  fi
  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# TIER 2 — Contextual nudges (user knows what they want, there's a better path)
# Softer suggestions — lower confidence, easy to ignore.
# ─────────────────────────────────────────────────────────────────────────────

# Scaffold intent → stack-specific scaffold command
if echo "$p" | grep -qE '\b(scaffold|create (a new|new)|set up|bootstrap|initialise|initialize|new (service|module|app|project|feature))\b'; then
  if echo "$p" | grep -qE '\b(flutter|dart)\b' && ! already_present "/scaffold-flutter"; then
    log_suggestion "2" "/scaffold-flutter-app" "false" "false"
    echo "💡 [smart-suggest Tier 2] New Flutter project? /scaffold-flutter-app sets up clean architecture, Riverpod, Freezed, and Firebase in one shot."
  elif echo "$p" | grep -qE '\b(nestjs|nest|node)\b' && ! already_present "/scaffold-nestjs"; then
    log_suggestion "2" "/scaffold-nestjs-api" "false" "false"
    echo "💡 [smart-suggest Tier 2] New NestJS service? /scaffold-nestjs-api generates module, controller, service, Prisma repo, DTOs, and Vitest tests."
  elif echo "$p" | grep -qE '\b(spring|java)\b' && ! already_present "/scaffold-spring"; then
    log_suggestion "2" "/scaffold-spring-api" "false" "false"
    echo "💡 [smart-suggest Tier 2] New Spring Boot service? /scaffold-spring-api sets up WebFlux, R2DBC, and reactive test infrastructure."
  elif echo "$p" | grep -qE '\b(angular)\b' && ! already_present "/scaffold-angular"; then
    log_suggestion "2" "/scaffold-angular-app" "false" "false"
    echo "💡 [smart-suggest Tier 2] New Angular app? /scaffold-angular-app sets up standalone components, signals, lazy routing, and daisyUI."
  elif echo "$p" | grep -qE '\b(python|fastapi)\b' && ! already_present "/scaffold-python"; then
    log_suggestion "2" "/scaffold-python-api" "false" "false"
    echo "💡 [smart-suggest Tier 2] New Python service? /scaffold-python-api sets up FastAPI, Pydantic v2, SQLAlchemy async, and pytest."
  fi
  exit 0
fi

# Long autonomous task → /ralph-loop
if echo "$p" | grep -qE '\b(keep (trying|fixing|running|iterating)|until (all|every|zero|done|complete|fixed|passing)|overnight|unattended|loop until)\b'; then
  if ! already_present "/ralph-loop" && ! already_present "/autoresearch"; then
    log_suggestion "2" "/ralph-loop" "false" "false"
    echo "💡 [smart-suggest Tier 2] Long autonomous task detected — /ralph-loop iterates until your completion promise is satisfied. /autoresearch if improving a quality metric."
  fi
  exit 0
fi

# No suggestion triggered — pass through silently
exit 0
