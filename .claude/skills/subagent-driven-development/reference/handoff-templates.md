
# SDD Handoff Templates

Human-readable structured context documents for the Implementer → Spec Reviewer → Quality Reviewer pipeline.

**Relationship to `handoff-tags.md`:** Tags are for machine parsing (compact, structured). Templates are for human review (readable, contextual). Use both: tags for agent-to-agent data transfer, templates when a human needs to review the handoff or when writing PR descriptions.

---

## Template 1 — Standard Task Handoff (Implementer → Spec Reviewer)

Use when passing a completed implementation to spec review.

```markdown
# Handoff: [Task Name]

## Metadata
- **From:** Implementer
- **To:** Spec Reviewer
- **Task:** [task ID and title]
- **Branch:** [branch name]
- **Timestamp:** [ISO date]

## What Was Built

[1–3 sentences describing what was implemented. Be specific — not "added the feature" but "added POST /orders endpoint with idempotency via orderRef, returning 201 with full order body or 409 on duplicate orderRef".]

## Files Changed

| File | What Changed |
|------|-------------|
| `path/to/file.ts` | [what changed and why] |
| `path/to/file.spec.ts` | [tests written — N tests, what they cover] |

## Tests

- Written: N tests
- Status: all pass / N failing (list failing tests)
- Coverage: [what paths are covered — happy path, error paths, edge cases]

## Self-Review Notes

[Anything the spec reviewer should pay attention to. If none: "No concerns."]

## Deferred / Out of Scope

[List anything explicitly not implemented and why. If none: "Nothing deferred."]

## Assumptions Made

[Any assumption not stated in the spec. If none: "No assumptions."]

## Spec Reviewer — What to Verify

- [ ] [Specific acceptance criterion from spec]
- [ ] [Specific acceptance criterion from spec]
- [ ] [Edge case worth checking]
```

---

## Template 2 — QA Pass Verdict (Spec Reviewer → Quality Reviewer)

Use when spec review passes and work advances to quality review.

```markdown
# Spec Review: PASS — [Task Name]

## Metadata
- **Reviewer:** Spec Reviewer
- **Task:** [task ID and title]
- **Verdict:** PASS / CONDITIONAL PASS

## Spec Compliance

| Requirement | Status | Evidence |
|-------------|--------|---------|
| [requirement from spec] | ✅ Confirmed | [file:line] |
| [requirement from spec] | ✅ Confirmed | [file:line] |

## Waived Items

[Any spec item explicitly waived with reason. If none: "None."]

## Notes for Quality Reviewer

[Anything the quality reviewer should pay extra attention to based on what was found during spec review. If none: "Standard review."]
```

---

## Template 3 — QA Fail Verdict (Spec Reviewer → Implementer)

Use when spec review finds issues that must be fixed before advancing.

```markdown
# Spec Review: CONDITIONAL PASS — [Task Name]

## Metadata
- **Reviewer:** Spec Reviewer
- **Task:** [task ID and title]
- **Verdict:** CONDITIONAL PASS — implementer must fix before quality review

## Issues Found

### Issue 1 — [Severity: Critical / High / Medium]
- **File:** `path/to/file.ts:line`
- **Problem:** [specific description]
- **Expected (per spec):** [what the spec says should happen]
- **Actual:** [what the code currently does]
- **Fix:** [concrete instruction for the implementer]

### Issue 2 — [Severity]
[same structure]

## Confirmed Items

[What was correctly implemented — so the implementer knows what NOT to change.]

## Re-review Instructions

After fixing the issues above, re-submit for spec review. Do not advance to quality review until spec review returns PASS.
```

---

## Template 4 — Quality Review: APPROVE

Use when quality review passes and the task is ready to merge.

```markdown
# Quality Review: APPROVE — [Task Name]

## Metadata
- **Reviewer:** Quality Reviewer
- **Task:** [task ID and title]
- **Verdict:** APPROVE

## Review Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Correctness | ✅ | [brief note or "clean"] |
| Security | ✅ | [brief note or "clean"] |
| Error handling | ✅ | [brief note or "clean"] |
| Tests | ✅ | [brief note or "clean"] |
| Spec compliance | ✅ | All spec reviewer issues resolved |

## Approved for Merge

No issues. Safe to merge once CI passes.
```

---

## Template 5 — Quality Review: BLOCK

Use when quality review finds issues that must be fixed before merge.

```markdown
# Quality Review: BLOCK — [Task Name]

## Metadata
- **Reviewer:** Quality Reviewer
- **Task:** [task ID and title]
- **Verdict:** BLOCK — [N] critical, [N] high, [N] medium issues

## Critical Issues (must fix before merge)

### [Issue Title]
- **File:** `path/to/file.ts:line`
- **Severity:** Critical / High
- **Problem:** [specific description]
- **Risk:** [what could go wrong in production]
- **Fix:** [concrete instruction]

## Medium Issues (should fix before merge)

### [Issue Title]
- **File:** `path/to/file.ts:line`
- **Problem:** [description]
- **Fix:** [instruction]

## Re-review Instructions

Fix all Critical and High issues. Medium issues should be addressed unless there is a documented reason to defer. After fixing, quality review re-runs (spec review does NOT re-run unless spec compliance was broken).
```

---

## Template 6 — Escalation Report (After 3 Failed Retries)

Use when a task has failed QA 3 times and needs human decision.

```markdown
# ESCALATION — [Task Name]

## Metadata
- **Task:** [task ID and title]
- **Attempts:** 3 (maximum reached)
- **Status:** Unresolved after 3 fix-review cycles

## Attempt History

### Attempt 1
- **Fix applied:** [what was changed]
- **QA result:** [what verdict was returned, what issues remained]

### Attempt 2
- **Fix applied:** [what was changed]
- **QA result:** [what issues remained]

### Attempt 3
- **Fix applied:** [what was changed]
- **QA result:** [what issues still remain]

## Remaining Issues

[List the issues that could not be resolved after 3 attempts, with file:line evidence.]

## Root Cause Assessment

[Why is this not resolving? Is it a spec ambiguity, an architectural constraint, a missing dependency, or a misunderstanding of requirements?]

## Options

A) **Provide direction** — clarify the requirement or suggest a different approach
B) **Decompose** — break this task into smaller sub-tasks
C) **Defer** — move this to a separate PR with a known gap documented
D) **Accept as-is** — approve with documented exceptions

→ Human decision required before proceeding.
```

---

## Template 7 — PR Description (Post-Pipeline)

Use when creating the PR after all tasks complete. Consolidates all deferred items from implementer tags.

```markdown
# [PR Title]

## Summary

[2–3 sentences describing what this PR does and why.]

## Changes

| Area | What Changed |
|------|-------------|
| [module/service] | [description] |
| [module/service] | [description] |

## Testing

- [ ] All existing tests pass
- [ ] New tests written for: [list]
- [ ] Manual verification: [describe what was tested manually]

## Quality Gates Passed

- [ ] Spec Reviewer: PASS on all tasks
- [ ] Quality Reviewer: APPROVE on all tasks
- [ ] Security: no CRITICAL/HIGH findings
- [ ] CI: all checks green

## Known Gaps / Deferred

[Consolidated from DEFERRED fields in all implementer handoff tags. If none: "None."]

| Item | Reason | Tracking |
|------|--------|---------|
| [deferred item] | [reason] | [ticket or "TODO"] |

## Related

- Plan: `docs/plans/[plan-file].md`
- Spec: `specs/[spec-file].spec.md` (if applicable)
```

---

## When to Use Templates vs Tags

| Situation | Use Tags | Use Templates |
|-----------|----------|---------------|
| Agent-to-agent data transfer | ✅ | — |
| Human reviewing a handoff | — | ✅ |
| PR description | — | ✅ (Template 7) |
| Orchestrator passing context | ✅ (verbatim) | — |
| Escalation to human | — | ✅ (Template 6) |
| Both (production pipeline) | ✅ | ✅ |
