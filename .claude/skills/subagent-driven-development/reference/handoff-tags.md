# SDD Handoff Tags

Structured handoff format for the Implementer → Spec Reviewer → Quality Reviewer pipeline.

Each role writes a tagged block at the END of its output. The next role reads it directly.
The orchestrator passes the tag block inline — never summarizes or paraphrases it.

---

## Tag Format

Tags use HTML comment syntax so they are ignored by renderers but readable by agents.

```
<!-- SDD:{role}:{task-slug} -->
{key}: {value}
<!-- /SDD:{role} -->
```

- `{role}`: `implementer` | `spec-reviewer` | `quality-reviewer`
- `{task-slug}`: kebab-case task title, e.g. `orders-create-endpoint`
- Keys are uppercase, values are free text or lists (one item per line, indented with `  - `)

---

## Role 1 — Implementer Output Tag

Written by the implementer at the end of its response. Required fields:

```
<!-- SDD:implementer:{task-slug} -->
FILES_CHANGED:
  - path/to/file.ts — what changed
  - path/to/file.spec.ts — tests written
TESTS_STATUS: N tests written, all pass | N tests written, N failing (list them)
SELF_REVIEW: no issues | list any concerns found during self-review
DEFERRED:
  - description of anything explicitly out of scope or deferred with reason
ASSUMPTIONS:
  - any assumption made that was not stated in the task spec
<!-- /SDD:implementer -->
```

**Example:**
```
<!-- SDD:implementer:orders-create-endpoint -->
FILES_CHANGED:
  - src/orders/orders.service.ts — createOrder method + validation
  - src/orders/orders.controller.ts — POST /orders endpoint
  - src/orders/orders.service.spec.ts — 14 unit tests
TESTS_STATUS: 14 tests written, all pass
SELF_REVIEW: no issues found
DEFERRED:
  - rate limiting not implemented — out of scope per plan task 3
ASSUMPTIONS:
  - orderRef uniqueness enforced at DB level via unique index (not validated in service)
<!-- /SDD:implementer -->
```

---

## Role 2 — Spec Reviewer Output Tag

Written by the spec reviewer at the end of its response. Required fields:

```
<!-- SDD:spec-reviewer:{task-slug} -->
VERDICT: PASS | CONDITIONAL PASS | BLOCK
OPEN_ISSUES:
  - file:line — description of issue (omit section if none)
RESOLVED:
  - list of spec items confirmed as correctly implemented
WAIVED:
  - description of any spec item explicitly waived with reason (omit if none)
<!-- /SDD:spec-reviewer -->
```

**Example — PASS:**
```
<!-- SDD:spec-reviewer:orders-create-endpoint -->
VERDICT: PASS
OPEN_ISSUES: none
RESOLVED:
  - POST /orders returns 201 with created order body ✅
  - validation rejects missing customerId with 400 ✅
  - idempotency via orderRef confirmed ✅
<!-- /SDD:spec-reviewer -->
```

**Example — CONDITIONAL PASS (implementer must fix before advancing):**
```
<!-- SDD:spec-reviewer:orders-create-endpoint -->
VERDICT: CONDITIONAL PASS
OPEN_ISSUES:
  - src/orders/orders.service.ts:45 — createOrder does not validate duplicate orderRef; spec requires 409 on duplicate
RESOLVED:
  - POST /orders returns 201 ✅
  - customerId validation ✅
<!-- /SDD:spec-reviewer -->
```

---

## Role 3 — Quality Reviewer Output Tag

Written by the quality reviewer at the end of its response. Required fields:

```
<!-- SDD:quality-reviewer:{task-slug} -->
VERDICT: APPROVE | NEEDS_REVIEW | BLOCK
CRITICAL: N
HIGH: N
MEDIUM: N
OPEN_ISSUES:
  - file:line — description (omit section if none)
SPEC_REVIEWER_ISSUES_RESOLVED: YES | NO — list any that were not
<!-- /SDD:quality-reviewer -->
```

**Example — APPROVE:**
```
<!-- SDD:quality-reviewer:orders-create-endpoint -->
VERDICT: APPROVE
CRITICAL: 0
HIGH: 0
MEDIUM: 0
OPEN_ISSUES: none
SPEC_REVIEWER_ISSUES_RESOLVED: YES
<!-- /SDD:quality-reviewer -->
```

**Example — BLOCK:**
```
<!-- SDD:quality-reviewer:orders-create-endpoint -->
VERDICT: BLOCK
CRITICAL: 1
HIGH: 0
MEDIUM: 1
OPEN_ISSUES:
  - src/orders/orders.service.ts:67 — CRITICAL: raw SQL string concatenation, SQL injection risk
  - src/orders/orders.service.spec.ts — MEDIUM: no test for 500 error path
SPEC_REVIEWER_ISSUES_RESOLVED: YES
<!-- /SDD:quality-reviewer -->
```

---

## How the Orchestrator Uses Tags

### Passing implementer tag to spec reviewer

Include the full implementer tag block verbatim in the spec reviewer prompt:

```
Task spec: [full task text]

Implementer output:
[full implementer response]

Implementer handoff tag:
<!-- SDD:implementer:{task-slug} -->
...
<!-- /SDD:implementer -->

Now perform spec compliance review.
```

### Passing both tags to quality reviewer

Include both tag blocks verbatim in the quality reviewer prompt:

```
Files changed: [list from implementer tag FILES_CHANGED]

Prior review context:
<!-- SDD:implementer:{task-slug} -->
...
<!-- /SDD:implementer -->

<!-- SDD:spec-reviewer:{task-slug} -->
...
<!-- /SDD:spec-reviewer -->

Now perform quality review on the changed files.
```

### Extracting deferred items for PR description

After all tasks complete, collect all `DEFERRED:` entries from implementer tags and include them in the PR body under a **Known Gaps / Deferred** section.

---

## Rules

- Tags are written by agents — never hand-crafted by the orchestrator
- The orchestrator copies tags verbatim — no summarizing, no paraphrasing
- If an agent forgets to write its tag, the orchestrator must ask it to add the tag before advancing the pipeline
- `CONDITIONAL PASS` from spec reviewer = implementer fixes required before quality review starts
- `BLOCK` from quality reviewer = implementer fixes required, then quality review re-runs (not spec review)
- Tags accumulate per task — by the end of Step 3, all 3 tags exist for each task
