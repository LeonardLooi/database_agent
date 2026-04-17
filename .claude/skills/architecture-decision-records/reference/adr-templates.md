# ADR Templates

Copy-paste templates for different ADR formats. Choose the format that fits the decision's complexity.

---

## Minimal Skeleton (Copy-Paste Starter)

Use for straightforward decisions where context is clear to the team.

```markdown
# ADR-NNNN: [Title]

## Status
Proposed | Accepted | Deprecated | Superseded by ADR-XXXX

## Context
[Why do we need to decide this? What's the problem?]

## Decision
We will [decision].

## Consequences
- **Good**: [benefits]
- **Bad**: [drawbacks]
- **Mitigations**: [how we'll address the bad]
```

---

## Standard ADR (MADR Format)

Use for significant decisions that need thorough analysis with multiple options.

```markdown
# ADR-NNNN: [Title]

## Status

[Proposed | Accepted | Deprecated | Superseded by ADR-XXXX]

## Context

[Describe the situation. What problem are we solving? What constraints exist?
Include relevant technical context, business requirements, and team considerations.]

## Decision Drivers

- **Must have [requirement]** for [reason]
- **Must support [capability]** for [use case]
- **Should support [feature]** to [benefit]
- **Team familiarity** with [technology]

## Considered Options

### Option 1: [Name]

- **Pros**: [advantages]
- **Cons**: [disadvantages]

### Option 2: [Name]

- **Pros**: [advantages]
- **Cons**: [disadvantages]

### Option 3: [Name]

- **Pros**: [advantages]
- **Cons**: [disadvantages]

## Option Scoring

Score each option using the dual-lens rubric in [`reference/adr-scoring.md`](adr-scoring.md).

| Option | Systems /50 | Developer /50 | Combined /100 | Verdict |
|--------|------------|---------------|---------------|---------|
| Option 1: [Name] | | | | ADOPT / ADOPT WITH MITIGATIONS / REVISIT / REJECT |
| Option 2: [Name] | | | | |
| Option 3: [Name] | | | | |

**Lens gap check:** [If any option's Systems and Developer scores differ by >20 points, name it here and explain what that gap means before proceeding to the decision.]

## Decision

We will use **[chosen option]**.

## Rationale

[Explain why this option was chosen. Reference decision drivers.
Address why other options were rejected.]

## Consequences

### Positive

- [benefit 1]
- [benefit 2]

### Negative

- [drawback 1]
- [drawback 2]

### Risks

- [risk 1]
- Mitigation: [how to address]

## Implementation Notes

- [specific implementation guidance]
- [configuration requirements]
- [timeline expectations]

## Related Decisions

- ADR-XXXX: [related decision] - [relationship]
```

---

## Lightweight ADR

Use for medium-complexity decisions where a full MADR is overkill.

```markdown
# ADR-NNNN: [Title]

**Status**: [Proposed | Accepted | Deprecated]
**Date**: YYYY-MM-DD
**Deciders**: @person1, @person2, @person3

## Context

[Brief description of the problem and constraints. 2-3 paragraphs maximum.]

## Decision

[What we decided. 1-2 sentences.]

## Consequences

**Good**: [benefits in 1-2 sentences]

**Bad**: [drawbacks in 1-2 sentences]

**Mitigations**: [how we address the downsides]
```

---

## Y-Statement Format (One-liner)

Use for simple technology selections where the trade-off is straightforward.

```markdown
# ADR-NNNN: [Title]

In the context of **[situation/project]**,
facing **[the specific problem or need]**,
we decided for **[chosen option]**
and against **[rejected options]**,
to achieve **[desired outcomes and qualities]**,
accepting that **[trade-offs and limitations]**.
```

---

## Deprecation ADR

Use when retiring a previous decision and migrating to a replacement.

```markdown
# ADR-NNNN: Deprecate [Old Choice] in Favor of [New Choice]

## Status

Accepted (Supersedes ADR-XXXX)

## Context

ADR-XXXX (YYYY) chose [old technology/pattern] for [reason]. Since then:

- [Change in circumstances 1]
- [Change in circumstances 2]
- [Change in circumstances 3]

## Decision

Deprecate [old choice] and migrate to [new choice].

## Migration Plan

1. **Phase 1** (Week X-Y): [setup, dual-write]
2. **Phase 2** (Week X-Y): [backfill, validate]
3. **Phase 3** (Week X-Y): [switch reads, monitor]
4. **Phase 4** (Week X-Y): [remove old, decommission]

## Consequences

### Positive

- [benefit 1]
- [benefit 2]

### Negative

- [cost 1]
- [risk 1]

## Lessons Learned

- [insight from the original decision]
- [what to consider for future decisions]
```

---

## RFC Style (For Major Proposals)

Use for large-scope proposals that need broad team input before becoming an ADR.

```markdown
# RFC-NNNN: [Title]

## Summary

[1-2 paragraph summary of the proposal]

## Motivation

Current challenges:

1. [Problem 1]
2. [Problem 2]
3. [Problem 3]

## Detailed Design

### [Component 1]

[Technical design details]

### [Component 2]

[Technical design details]

### Technology

- [Technology choice and rationale]
- Alternative considered: [alternative and why rejected]

## Drawbacks

- [Drawback 1]
- [Drawback 2]

## Alternatives

1. **[Alternative 1]**: [description and trade-off]
2. **[Alternative 2]**: [description and trade-off]

## Unresolved Questions

- [ ] [Question 1]
- [ ] [Question 2]

## Implementation Plan

1. [Phase 1] (timeline)
2. [Phase 2] (timeline)
3. [Phase 3] (timeline)

## References

- [External reference 1]
- [External reference 2]
```

---

## Choosing a Template

| Decision Complexity | Template | Typical Length |
|---------------------|----------|---------------|
| Simple tech selection | Y-Statement | 1 paragraph |
| Medium decision | Lightweight ADR | 0.5-1 page |
| Significant architecture change | Standard MADR | 1-2 pages |
| Retiring a decision | Deprecation ADR | 1-2 pages |
| Major cross-team proposal | RFC Style | 2-4 pages |
