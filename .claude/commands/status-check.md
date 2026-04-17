---
description: Binary status report showing what works, what's broken, and what's not implemented. No percentages, no hedging.
allowed-tools: Bash, Read, Glob, Grep
---

# Status Check

Give me an honest status report. Follow these rules STRICTLY:

## Format Required

```
## What WORKS (end-to-end, no caveats)
- [Feature]: ✅ User can [specific action]

## What's BROKEN (non-functional)
- [Feature]: ❌ [What happens] instead of [what should happen]

## What's NOT IMPLEMENTED (doesn't exist yet)
- [Feature]: 🚫 Not built
```

## Rules

1. **NO PERCENTAGES** - Never say "90% done" or "mostly complete"
2. **NO CONTRADICTIONS** - If you list issues, it's BROKEN, not "works with issues"
3. **BINARY ONLY** - Either it WORKS end-to-end or it's BROKEN
4. **NO HEDGING** - No "almost", "nearly", "mostly", "partially"
5. **MATCH SUMMARY TO DETAILS** - If details show problems, summary must say BROKEN

## Self-Check Before Responding

Ask yourself:
- Did I say something "works" then list why it doesn't? → REWRITE
- Did I use a percentage? → REMOVE IT
- Did I use "mostly/almost/nearly"? → REPLACE with WORKS or BROKEN

$ARGUMENTS
