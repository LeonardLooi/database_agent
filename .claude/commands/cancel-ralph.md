---
description: Cancel an active Ralph loop immediately. Deletes the state file so the loop stops on the next turn exit.
---

# Cancel Ralph Loop

```bash
RALPH_STATE_FILE="$CLAUDE_PROJECT_DIR/.claude/ralph-loop.local.md"

if [[ -f "$RALPH_STATE_FILE" ]]; then
  ITERATION=$(grep '^iteration:' "$RALPH_STATE_FILE" | sed 's/iteration: *//')
  rm "$RALPH_STATE_FILE"
  echo "🛑 Ralph loop cancelled after iteration ${ITERATION:-?}."
  echo "   The loop will exit cleanly on the next turn."
else
  echo "ℹ️  No active Ralph loop found."
fi
```
