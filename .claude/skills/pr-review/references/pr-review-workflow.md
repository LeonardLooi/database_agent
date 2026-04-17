# PR Review Workflow Details

## Complete Step-by-Step

### 1. Trigger

User says: "Review PR #42" or "Give feedback on this PR" or "I need to review this PR"

### 2. Fetch PR Data (Stage 1 start)

```bash
# All metadata in one call
gh pr view 42 --json number,title,body,author,additions,deletions,changedFiles,baseRefName,headRefName

# Full diff of all changes
gh pr diff 42

# Existing review comments and status
gh pr view 42 --json comments,reviews,reviewRequests

# CI/CD check results
gh pr checks 42
```

### 3. Optional: Run /review-pr for Structured Findings

Before writing review.md, get systematic findings across all 6 concern areas:
```
/review-pr [paste the diff or specify the PR branch]
```
Feed the aggregated output into the Findings section of review.md.

### 4. Write review.md (Internal)

```markdown
# PR Review: [title] (#number)
**Author:** [name] | **Branch:** [head] -> [base] | **Changes:** +N/-N lines

## Summary
[1-2 sentences: what this PR does and its overall quality]

## Findings

### Blocking (must fix before merge)
- [file:line] [description] — [why this blocks merge]

### Important (should fix)
- [file:line] [description]

### Suggestions (optional)
- [file:line] [description]

### Positive (what was done well)
- [observation]

## Decision
[APPROVE / REQUEST CHANGES / COMMENT]
[1-2 sentences of reasoning]
```

### 5. Write human.md (Public)

```markdown
## PR Review

[One positive opening sentence about what the PR does well.]

**Blocking issues (must address before merge):**
- [Clear description without file:line refs or internal notes]

**Important improvements:**
- [Description]

**Suggestions (optional):**
- [Description]

---
[LGTM! / Please address the blocking issues above before this can merge. Happy to re-review after.]
```

Rules for human.md:
- No emojis
- No `file:line` references (they look mechanical in GitHub comments)
- No internal analysis notes or reasoning
- Constructive and specific — say what to change, not just that it's wrong
- Always lead with something genuine and positive
- Keep it concise — PR authors skim long reviews

### 6. Human Approval Gate

```bash
# Open for review and editing
code pr/review.md pr/human.md
# or
open pr/review.md && open pr/human.md
```

Read both. Edit human.md until you're satisfied. Nothing posts until you run the next step.

### 7. Post to GitHub (Stage 2)

```bash
# Approve + comment
gh pr review 42 --approve --body "$(cat pr/human.md)"

# Request changes + comment
gh pr review 42 --request-changes --body "$(cat pr/human.md)"

# Comment only (use when you have questions but no blocking issues)
gh pr review 42 --comment --body "$(cat pr/human.md)"
```

### 8. Inline Comments (Optional, Post-Stage 2)

Get the commit SHA first:
```bash
COMMIT=$(gh pr view 42 --json headRefOid --jq .headRefOid)
REPO=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
```

Post a specific line comment:
```bash
gh api /repos/$REPO/pulls/42/comments \
  --method POST \
  -f body="Consider using Optional here to make nullability explicit" \
  -f path="src/user/UserService.java" \
  -f position=42 \
  -f commit_id="$COMMIT"
```

Structure pr/inline.md as one ready-to-run command per comment. Pick and run only the ones you agree with.

## When to Choose Each Decision

| Situation | Decision | Command flag |
|-----------|---------|--------------|
| No blocking issues, code looks good | Approve | --approve |
| Blocking issues must be fixed | Request changes | --request-changes |
| Questions but no blockers yet | Comment | --comment |
| Minor suggestions only | Approve + note suggestions | --approve |
| Uncertain about intent | Comment (ask for clarification first) | --comment |
