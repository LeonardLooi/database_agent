---
description: Autonomously iterate on the current PR until all CI checks pass and all high/medium review feedback is addressed
allowed-tools: Bash, Read, Glob, Grep
---

Load and execute the `iterate-pr` skill.

Autonomously iterate on the current branch's PR until all CI checks pass and all high/medium review feedback is addressed. Run from the repository root.

Steps:
1. Load `.claude/skills/iterate-pr/SKILL.md` for the full 8-step workflow
2. Confirm a PR exists for the current branch (`gh pr view`)
3. Run the complete iterate-pr loop until exit conditions are met

Arguments: $ARGUMENTS (optional PR number — if omitted, uses current branch PR)
