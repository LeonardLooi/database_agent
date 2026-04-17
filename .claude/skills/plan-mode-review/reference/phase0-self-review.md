# Phase 0: Self-Review Loop

> Run BEFORE any code review or implementation. The goal is to prevent building the wrong thing faster.

**Philosophy:** Speed is easy. Restraint is the skill. The code you don't write is more valuable than the code you do.

---

## Step 0.1 — Spec the Outcome, Not the Implementation

Ask: **"What does DONE look like?"** — not how to build it, but what the end result should be.

1. Define clear acceptance criteria: what must be true when this is finished?
2. Express the outcome in **user/business terms**, not technical terms
3. Generate a diagram of the **desired end state** from the user's perspective (data flow, user journey, or system boundary — whatever fits)

### Output Template

```
## Outcome Spec
**Goal:** [one sentence in user/business terms]

**Acceptance Criteria:**
- [ ] [simple criterion — for UI/config/static checks]

**Key Scenarios** (for behavioral requirements):
#### Scenario: [name]
- **WHEN** [condition or user action]
- **THEN** [expected outcome, observable and testable]

#### Scenario: [name — unhappy path]
- **WHEN** [error condition or edge case]
- **THEN** [expected error behavior]

**Constraints** (non-functional requirements):
| Category | Constraint |
|----------|-----------|
| Performance | [e.g., response <200ms at p95] |
| Compatibility | [e.g., must not break existing API contract] |
| Security | [e.g., must not expose PII in logs] |
| Operational | [e.g., must work with zero downtime deployment] |
> Skip categories that don't apply. Add categories that do.

**End State Diagram:**
[Mermaid or ASCII diagram here]
```

---

## Step 0.2 — Propose 3 Approaches, Recommend the Leanest

Propose **3 distinct implementation approaches** to achieve the outcome.

**Rules:**
- Always consider whether a **no-code or config-only** approach is feasible (feature flag, env var, removing code, changing config, leveraging an existing tool). Include it as one of the 3 if viable.
- For each approach: LOC estimate is order-of-magnitude, not precise

### Output Template

```
## Approach Comparison

### Approach A: [Name]
- **Description:** [2-3 sentences]
- **Estimate:** ~X LOC / Y files / Z complexity
- **Tradeoff:** [what you gain vs what you give up]
- **Diagram:**
  [high-level Mermaid or ASCII]

### Approach B: [Name]
- **Description:** [2-3 sentences]
- **Estimate:** ~X LOC / Y files / Z complexity
- **Tradeoff:** [what you gain vs what you give up]
- **Diagram:**
  [high-level Mermaid or ASCII]

### Approach C: [Name]
- **Description:** [2-3 sentences]
- **Estimate:** ~X LOC / Y files / Z complexity
- **Tradeoff:** [what you gain vs what you give up]
- **Diagram:**
  [high-level Mermaid or ASCII]

**Recommendation:** Approach [X] — [one sentence why it's the leanest
that fully satisfies the outcome]
```

Wait for the user to pick an approach before proceeding.

---

## Step 0.3 — Self-Review: Attack Your Own Recommendation

Immediately after recommending, challenge it:

| Question | Answer |
|----------|--------|
| What edge cases does this miss? | [list] |
| Where is this over-engineered? | [what can be simplified] |
| Where is this under-engineered? | [what will break in production] |
| What assumptions are baked in? | [list assumptions that might be wrong] |
| Confidence rating | Low / Medium / High — [explain why] |

Present this self-critique transparently. Do not hide doubts.

---

## Step 0.4 — Deletion Pass

Ask: **"What can we NOT build and still hit the outcome?"**

For every component, feature, abstraction, or config in the selected approach:

| Component | Can Defer? | What We Lose | Matters for Outcome? |
|-----------|-----------|--------------|---------------------|
| [component] | Yes/No | [impact] | Yes/No |

Generate a **Minimal Build Diagram** — the absolute smallest version that satisfies the outcome spec.

Ask the user to confirm what stays and what gets cut.

---

## Step 0.5 — Gate Check

Before proceeding to review phases, ALL must be true:

```
PHASE 0 GATE:
- [ ] Outcome is clearly defined with scenarios and constraints (Step 0.1)
- [ ] Leanest approach is selected (Step 0.2)
- [ ] Self-review surfaced and addressed edge cases (Step 0.3)
- [ ] Deletion pass completed — we know what we're NOT building (Step 0.4)
- [ ] Human approved the direction
```

**If ANY item is unchecked: STOP. Do not proceed. Ask for what's missing.**

---

## Quick Reference: Phase 0 vs Existing Rules

Phase 0 extends (does not replace) the existing Task Response Protocol from `leverage-patterns.md`:

| Existing (leverage-patterns.md) | Phase 0 Addition |
|-------------------------------|------------------|
| UNDERSTAND: Restate the task | Step 0.1: Spec the outcome in business terms |
| PLAN: 3-5 bullet approach | Step 0.2: 3 full approaches with estimates and diagrams |
| DECISIONS: List tradeoffs | Step 0.3: Self-critique with confidence rating |
| (not covered) | Step 0.4: Deletion pass — what NOT to build |
| (not covered) | Step 0.5: Formal gate check before proceeding |
