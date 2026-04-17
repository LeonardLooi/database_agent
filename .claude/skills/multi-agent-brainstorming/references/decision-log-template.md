# Decision Log Template

The Decision Log is a mandatory artifact. No design is valid without a completed log.

Start the log at the beginning of Phase 1. Update it after every reviewer interaction.

---

## Template

```markdown
# Decision Log: [Design Name]

**Date:** [YYYY-MM-DD]
**Designer:** [name or "Claude Code"]
**Status:** IN REVIEW | APPROVED | REVISE | REJECT

---

## Understanding Lock

**Goal:** [What are we building and why?]

**Constraints:**
- Technical: [e.g., must work within existing NestJS monolith]
- Resource: [e.g., no additional infrastructure budget]
- Time: [e.g., must deploy by YYYY-MM-DD]

**Assumptions:**
- [Assumption 1: e.g., "User auth is handled upstream; this service receives a validated JWT"]
- [Assumption 2: e.g., "Peak load < 500 RPS in the first 6 months"]

---

## Design Summary

[2-3 sentence description of the chosen approach]

**Key decisions:**
1. [Decision 1: e.g., "Use PostgreSQL outbox pattern instead of direct Kafka publish"]
2. [Decision 2: e.g., "Store session in Redis, not in-memory"]

**Alternatives considered:**
- [Alternative A]: [Why not chosen]
- [Alternative B]: [Why not chosen]

---

## Review Record

### Skeptic Review

| Objection | Resolution | Status |
|-----------|------------|--------|
| [objection text] | [how it was addressed] | RESOLVED / REJECTED (rationale) |

### Constraint Guardian Review

| Objection | Resolution | Status |
|-----------|------------|--------|
| [objection text] | [how it was addressed] | RESOLVED / REJECTED (rationale) |

### User Advocate Review

| Objection | Resolution | Status |
|-----------|------------|--------|
| [objection text] | [how it was addressed] | RESOLVED / REJECTED (rationale) |

---

## Arbiter Verdict

**Verdict:** APPROVED | REVISE | REJECT

**Rationale:** [One paragraph explaining the verdict]

**Required changes (if REVISE):**
1. [Specific change required]
2. [Specific change required]

**Next step:** [proceed to /plan-review | revise and re-review | abandon]
```

---

## Rules

- Log every objection — even ones immediately dismissed
- Record the rationale for every rejected objection
- Never modify past entries — append corrections as new rows
- Decision Log must be complete before Phase 3 arbitration begins
