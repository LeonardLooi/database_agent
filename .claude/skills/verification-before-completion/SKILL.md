---
name: verification-before-completion
description: "Pre-completion verification checklist that mandates running tests, linting, and build commands before claiming work is done, fixed, or passing. Use before any commit, PR creation, or completion claim — evidence must precede assertions; triggers: done, complete, finished, working, before committing, before PR."
allowed-tools: Read, Bash
metadata:
  triggers: verification, done, complete, finished, working, before committing, before PR, verify before claiming
  related-skills: test-driven-development, systematic-debugging, pr-review
  domain: workflow
  role: specialist
  scope: review
  output-format: report
last-reviewed: "2026-03-15"
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If you haven't run the verification command in this message, you cannot claim it passes.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN: Execute the FULL command (fresh, complete)
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Test command output: 0 failures | Previous run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |
| PR task complete | GitHub Actions CI green + deployment workflow succeeded | PR merged |

## Red Flags — STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without having run verification**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Regression tests (TDD Red-Green):**
```
✅ Write → Run (pass) → Revert fix → Run (MUST FAIL) → Restore → Run (pass)
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

**Post-merge deployment (GitHub Actions via `github` MCP):**
```
✅ PR merged → Check Actions run → CI green + deploy workflow succeeded → Task complete
❌ "PR merged" (deployment may have failed silently)
```

## Post-Merge Verification

When a task involves a PR that has been merged, "done" means the deployment succeeded — not just that the code was merged. Use the `github` MCP (already configured) to check:

```
1. gh run list --branch main --limit 5          # list recent workflow runs
2. gh run view <run-id>                         # inspect CI + deploy workflow
3. All jobs: ✅ green → task is complete
   Any job: ❌ failed → task is NOT complete — investigate and fix
```

This costs nothing — the `github` MCP is already in `.mcp.json`. The agent can check deployment status directly without leaving the session.

**Trigger:** Apply this check whenever:
- A PR was merged as part of the task
- The task description included deployment or release
- The human says "it's merged" or "it's deployed"

**Do NOT skip this step** by assuming merge = success. CI can pass locally and fail in the pipeline (environment variables, container build, migration runner).

## Test Command by Stack

When about to claim tests pass, first confirm you're running the right command. Pick by what files are in the changed set:

| Project marker / changed files | Test command |
|--------------------------------|--------------|
| `pom.xml` or `*.java` | `mvn test -q` |
| `nest-cli.json` or `*.ts` with NestJS imports | `npm test` |
| `pyproject.toml` or `*.py` (FastAPI / plain Python) | `pytest -q` |
| `pubspec.yaml` or `*.dart` | `flutter test` |
| `angular.json` or `*.ts` with Angular imports | `ng test --watch=false` |
| `pyproject.toml` + LangGraph/LangChain imports | `pytest -q` |

**If multiple markers match** (e.g., a monorepo with Java + TypeScript), run the test command for each changed service separately.

**Never run the wrong stack's test command** — `npm test` in a Python project exits 0 with no output, giving false confidence.

## Why This Matters

Verification failures lead to:
- Broken trust ("I don't believe you")
- Undefined functions shipped — would crash
- Missing requirements shipped — incomplete features
- Time wasted on false completion → redirect → rework

This rule exists because honesty is a core value. Unverified claims are not efficiency — they are debt.

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Moving to next task
- Delegating to agents

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## The Bottom Line

**No shortcuts for verification.**

Run the command. Read the output. THEN claim the result.

This is non-negotiable.
