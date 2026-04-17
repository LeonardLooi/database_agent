# Iterate-PR Workflow Reference

Full 8-step operational procedure for the iterate-pr loop.

---

## Step 1 — Identify PR

```bash
gh pr view --json number,url,headRefName
```

Stop immediately if no PR exists for the current branch.

---

## Step 2 — Gather Review Feedback

```bash
uv run ${CLAUDE_SKILL_ROOT}/scripts/fetch_pr_feedback.py
```

Returns feedback categorized by LOGAF level.

---

## Step 3 — Handle Feedback by Priority

**Auto-fix without asking:** `high` (blockers, security, changes requested), `medium` (standard feedback)

**Prompt user for `low` items:**
```
Found N low-priority suggestions:
1. [l] "Rename this variable" — @reviewer in api.py:42
2. [nit] "Use list comprehension" — @reviewer in utils.py:18
Which would you like to address? (e.g., "1,2" or "all" or "none")
```

**Skip silently:** `resolved` threads, `bot` informational bots (Codecov, Dependabot)

**Review bot items** (`review_bot: true`) in high/medium/low — treat as human feedback:
- Real issue → fix it
- False positive → skip, reply explaining why

### Replying to Inline Review Comments

After processing each item with a `thread_id`:

```bash
gh api graphql -f query='
  mutation($threadId: ID!, $body: String!) {
    addPullRequestReviewThreadReply(input: {pullRequestReviewThreadId: $threadId, body: $body}) {
      comment { id }
    }
  }' -f threadId="<thread_id>" -f body="<reply>\n\n*— Claude Code*"
```

Rules:
- Reply = 1-2 sentences: what changed, why not an issue, or acknowledgment
- End every reply with `\n\n*— Claude Code*`
- Check thread first — skip if reply ending with `*- Claude Code*` already exists
- If `gh api` fails: log and continue, do NOT block the loop

---

## Step 4 — Check CI Status

```bash
uv run ${CLAUDE_SKILL_ROOT}/scripts/fetch_pr_checks.py
```

**Wait for review bots before proceeding:** sentry, warden, cursor, bugbot, seer, codeql — they post actionable feedback. Informational bots (codecov) don't block.

---

## Step 5 — Fix CI Failures

For each failure in `fetch_pr_checks.py` output:

1. Read `log_snippet` — trace root cause, not just the symptom
2. Read relevant source files; check for related issues nearby
3. Fix root cause with minimal, targeted changes
4. Run existing tests for the affected area
5. If fix introduces uncovered behavior — extend existing tests (add a test case, not a new file)

Do NOT assume the failure from check name alone. Always read the logs first.

---

## Step 6 — Verify Locally, Then Commit and Push

Before committing:
- Fixed a test failure → re-run that specific test
- Fixed a lint/type error → re-run linter/type-checker on affected files
- Any code fix → run existing tests covering changed code

Do NOT push known-broken code.

```bash
git add <specific files>
git commit -m "fix: <descriptive message>"
git push
```

---

## Step 7 — Monitor CI and Address New Feedback

Poll loop (do not block):

1. `uv run ${CLAUDE_SKILL_ROOT}/scripts/fetch_pr_checks.py` — get current status
2. All checks passed → proceed to exit conditions
3. Any checks failed (none pending) → return to Step 5
4. Checks still pending:
   a. `uv run ${CLAUDE_SKILL_ROOT}/scripts/fetch_pr_feedback.py` — check for new feedback
   b. Address new high/medium feedback immediately (same as Step 3)
   c. If changes needed → commit and push (restarts CI), continue polling
   d. Sleep 30 seconds, repeat from 4a
5. After all checks pass → `sleep 10`, final `fetch_pr_feedback.py`. Address any new high/medium — if changes needed, return to Step 6.

---

## Step 8 — Repeat

If Step 7 required code changes from new feedback, return to Step 2 for a fresh cycle.

---

## Exit Conditions

**Success:** All checks pass + post-CI feedback re-check clean + user decided on all low items.

**Ask for help:** Same failure after 2 attempts, feedback needs clarification, infrastructure issues.

**Stop:** No PR exists, branch needs rebase.

**Circuit breaker:** 6 full cycles completed without reaching Success. Escalate with full attempt history. Do not continue autonomously.

---

## Fallback (if scripts fail)

```bash
gh pr checks --json name,state,bucket,link
gh run view <run-id> --log-failed
gh api repos/{owner}/{repo}/pulls/{number}/comments
```
