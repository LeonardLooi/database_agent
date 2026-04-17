---
description: Start a Ralph Wiggum autonomous iteration loop. Claude works on the task, and when it tries to exit, the stop hook feeds the same prompt back until done. Use for long autonomous tasks, overnight work, or multi-attempt problems.
argument-hint: '"PROMPT" [--max-iterations N] [--completion-promise "TEXT"]'
---

# Ralph Loop

Start an autonomous iteration loop for the given task.

## Setup

```bash
# Parse arguments and create state file
ARGS="$ARGUMENTS"
PROMPT_PARTS=()
MAX_ITERATIONS=10
COMPLETION_PROMISE="null"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations)
      MAX_ITERATIONS="$2"; shift 2 ;;
    --completion-promise)
      COMPLETION_PROMISE="$2"; shift 2 ;;
    *)
      PROMPT_PARTS+=("$1"); shift ;;
  esac
done
PROMPT="${PROMPT_PARTS[*]}"

if [[ -z "$PROMPT" ]]; then
  echo "❌ No prompt provided. Usage: /ralph-loop \"Your task\" --max-iterations 10"
  exit 1
fi

mkdir -p "$CLAUDE_PROJECT_DIR/.claude"

if [[ "$COMPLETION_PROMISE" != "null" ]]; then
  CP_YAML="\"$COMPLETION_PROMISE\""
else
  CP_YAML="null"
fi

cat > "$CLAUDE_PROJECT_DIR/.claude/ralph-loop.local.md" <<EOF
---
active: true
iteration: 1
max_iterations: $MAX_ITERATIONS
completion_promise: $CP_YAML
started_at: "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
---

$PROMPT
EOF

echo ""
echo "🔄 Ralph loop activated!"
echo "   Iteration:   1 of $(if [[ $MAX_ITERATIONS -gt 0 ]]; then echo $MAX_ITERATIONS; else echo '∞ (unlimited)'; fi)"
if [[ "$COMPLETION_PROMISE" != "null" ]]; then
  echo "   Promise:     $COMPLETION_PROMISE"
  echo ""
  echo "═══════════════════════════════════════════════"
  echo "  To exit: output <promise>$COMPLETION_PROMISE</promise>"
  echo "  ONLY when the statement is GENUINELY TRUE."
  echo "  Do NOT output a false promise to escape."
  echo "═══════════════════════════════════════════════"
fi
echo ""
echo "  Monitor:  head -5 .claude/ralph-loop.local.md"
echo "  Cancel:   /cancel-ralph"
echo ""
```

Work on this task. You will see your previous work in files and git history each iteration.

**RULES:**
1. If `--completion-promise` is set, output `<promise>EXACT_TEXT</promise>` ONLY when the statement is genuinely and completely true
2. Do NOT lie to escape — the loop is designed to run until real completion
3. Use TaskList, git log, and modified files to track progress across iterations

$ARGUMENTS
