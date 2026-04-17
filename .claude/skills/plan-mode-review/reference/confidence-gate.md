# Phase 0.5: Confidence Gate — Scoring Reference

> **When to use:** Big Change mode only, after Phase 0 gate passes, before Phase 1.
> Skip for Small Change and Review Only modes.

---

## Thresholds

| Score | Decision |
|-------|----------|
| ≥ 95% | **Required** for irreversible changes (schema migrations, public API contracts, auth architecture) |
| ≥ 80% | **Proceed** to Phase 1 for all other changes |
| 60–79% | **Blocked** — address listed gaps, re-score |
| < 60% | **STOP** — plan needs significant rework before review |

---

## Scoring Rubric

### Dimension 1: Requirement Clarity

Are user stories, edge cases, acceptance criteria, and dependencies fully defined?

| Score | Meaning |
|-------|---------|
| 100 | All user stories defined with WHEN/THEN scenarios; all edge cases documented; acceptance criteria are measurable and testable; all dependencies (services, APIs, data) identified |
| 75 | Most stories and edge cases covered; acceptance criteria defined but some are vague; one or two dependencies unclear |
| 50 | Core happy path defined; edge cases partially documented; acceptance criteria exist but are not measurable; several dependencies unidentified |
| 25 | Requirements are described at a high level only; no WHEN/THEN scenarios; acceptance criteria absent or unmeasurable |
| 0 | No defined requirements; acceptance criteria completely absent; dependencies unknown |

### Dimension 2: Technical Feasibility

Is the architecture proven, APIs verified, and performance implications understood?

| Score | Meaning |
|-------|---------|
| 100 | Architecture approach used successfully before in this codebase; all external APIs verified against current docs (via MCP or official source); performance implications quantified; no unknown unknowns |
| 75 | Architecture is well-understood; most APIs verified; one performance concern identified but not fully quantified; no blockers |
| 50 | Architecture is plausible but not verified; some APIs checked, others assumed; performance implications unknown for at least one path |
| 25 | Architecture is novel or unproven; APIs assumed from memory without verification; significant unknown unknowns present |
| 0 | Approach is speculative; no APIs verified; unknowns dominate the plan |

### Dimension 3: Resource Assessment

Is the scope realistic and are all dependencies available?

| Score | Meaning |
|-------|---------|
| 100 | Scope fits comfortably in one session; all dependencies (packages, services, credentials) confirmed available; no unverified external APIs in the critical path |
| 75 | Scope is achievable; one dependency needs confirmation but has a fallback; external APIs are documented and accessible |
| 50 | Scope is at the edge of one session; one or more dependencies are uncertain; at least one external API is unverified in the current environment |
| 25 | Scope likely spans multiple sessions; critical dependencies unconfirmed; external APIs required but not accessible |
| 0 | Scope is indeterminate; core dependencies unavailable or unknown |

### Dimension 4: Quality Assurance

Is there a test strategy, rollback plan, and understood security impact?

| Score | Meaning |
|-------|---------|
| 100 | Test strategy defined (unit, integration, e2e coverage identified); rollback plan exists and is reversible; security implications reviewed (auth, input validation, data exposure); no open security questions |
| 75 | Test strategy covers happy path and major edge cases; rollback plan exists but partially manual; security implications identified, no critical gaps |
| 50 | Test strategy covers happy path only; rollback plan is vague; security implications partially assessed |
| 25 | No formal test strategy; rollback is "redeploy the old version" without specifics; security impact not assessed |
| 0 | No testing planned; no rollback plan; security not considered |

---

## Output Format

```
## Phase 0.5: Confidence Gate

| Dimension | Score |
|-----------|-------|
| Requirement Clarity | XX/100 |
| Technical Feasibility | XX/100 |
| Resource Assessment | XX/100 |
| Quality Assurance | XX/100 |

OVERALL CONFIDENCE: (D1 + D2 + D3 + D4) / 4 = XX%

[≥ 80%] → Proceed to Phase 1
[60–79%] → Address gaps listed below before proceeding
[< 60%] → STOP — plan needs significant work

Gaps to resolve before proceeding:
- [Dimension name]: [specific question that could not be answered — be precise]
- [Dimension name]: [specific question that could not be answered — be precise]
```

---

## Gap Severity Examples

### Low-severity gap (does not block at ≥ 80%)
- "Requirement Clarity: one edge case (concurrent writes) not documented — low frequency, acceptable to defer"
- "Quality Assurance: e2e test strategy not defined — unit + integration coverage is sufficient for this scope"

### Medium-severity gap (drops score to 60–79%, blocks until resolved)
- "Technical Feasibility: pagination API signature assumed from memory — must verify against MCP docs before coding"
- "Resource Assessment: Redis dependency needed for caching layer — availability in current environment unconfirmed"

### High-severity gap (drops score below 60%, hard stop)
- "Technical Feasibility: the core algorithm is novel and unproven — prototype required before full plan review"
- "Requirement Clarity: no acceptance criteria defined — cannot determine when the work is done"
- "Quality Assurance: no rollback plan for schema migration — irreversible change with no recovery path"

---

## Recovery Actions by Gap Pattern

| Gap Pattern | Recovery Action |
|-------------|----------------|
| Technical Feasibility < 50% | Verify the specific API or approach against MCP docs (or Context7 as fallback) before re-scoring. Do not rely on memory. |
| Requirement Clarity < 50% | Return to Phase 0, Step 0.1 — rewrite the outcome spec with explicit WHEN/THEN scenarios and measurable acceptance criteria. |
| Resource Assessment < 50% | Confirm each dependency is reachable in the current environment before proceeding. If a dependency is unavailable, scope the plan to exclude it or select an alternative. |
| Quality Assurance < 50% | Define a minimal test plan (which tests, at which layer) and a concrete rollback procedure before re-scoring. For irreversible changes, both are mandatory. |
| Any single dimension = 0 | STOP regardless of overall score. A zero in any dimension is a hard block. |

---

## Irreversible Change Checklist

Apply the 95% threshold when ANY of the following are true:

- [ ] Schema migration with no down migration
- [ ] Public API contract change that breaks existing consumers
- [ ] Auth architecture change (token format, session model, permission model)
- [ ] Data deletion or transformation with no backup/restore path
- [ ] External service integration with no sandbox/staging environment

For irreversible changes, all four dimensions must be ≥ 90 individually (average ≥ 95). A single dimension at 75 fails the gate even if the average is ≥ 95.

---

## Relationship to Phase 0

Phase 0 (Self-Review) asks qualitative questions to ensure the right thing is being built. Phase 0.5 quantifies the readiness to execute on the selected approach. A plan that passes Phase 0 may still fail Phase 0.5 if:

- The selected approach relies on unverified APIs
- The scope is not achievable in one session
- No rollback plan exists for a destructive operation
- Security implications were not assessed

Both gates must pass before moving to Phase 1.
