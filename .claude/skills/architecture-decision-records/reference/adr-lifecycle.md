# ADR Lifecycle

Manage ADR status transitions, deprecation patterns, review processes, and directory organization.

---

## Status Lifecycle

```
Proposed --> Accepted --> Deprecated --> Superseded
                |
             Rejected
```

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet decided |
| **Accepted** | Decision made, implementing or implemented |
| **Deprecated** | No longer relevant due to changed circumstances |
| **Superseded** | Replaced by a newer ADR (link to replacement) |
| **Rejected** | Considered but not adopted (still valuable context) |

### Transition Rules

- **Proposed to Accepted**: Requires review approval (2+ senior engineers)
- **Proposed to Rejected**: Document why -- rejected ADRs prevent re-litigating decisions
- **Accepted to Deprecated**: Circumstances changed, decision no longer applies
- **Accepted to Superseded**: New ADR explicitly replaces this one (link both directions)
- **Never edit accepted ADRs**: Write a new ADR that supersedes the old one

---

## Deprecation Patterns

### When to Deprecate

- Technology is being retired or replaced
- Business requirements have fundamentally changed
- The decision proved wrong and needs reversal
- External constraints have changed (licensing, security, compliance)

### Deprecation Process

1. Write a new ADR with status "Accepted (Supersedes ADR-XXXX)"
2. Update the original ADR's status to "Superseded by ADR-YYYY"
3. Do NOT modify the original ADR's content -- it is historical record
4. Include a "Lessons Learned" section in the new ADR

### Example Status Update (Original ADR)

```markdown
## Status

~~Accepted~~ Superseded by [ADR-0020](0020-deprecate-mongodb.md)
```

---

## Review Process

### Before Submission

- [ ] Context clearly explains the problem
- [ ] All viable options considered (minimum 2-3)
- [ ] Pros/cons balanced and honest
- [ ] Consequences (positive and negative) documented
- [ ] Related ADRs linked

### During Review

- [ ] At least 2 senior engineers reviewed
- [ ] Affected teams consulted
- [ ] Security implications considered
- [ ] Cost implications documented
- [ ] Reversibility assessed

### After Acceptance

- [ ] ADR index updated
- [ ] Team notified
- [ ] Implementation tickets created
- [ ] Related documentation updated

---

## Directory Structure

```
docs/
  adr/
    README.md           # Index and guidelines
    template.md         # Team's ADR template
    0001-use-postgresql.md
    0002-caching-strategy.md
    0003-mongodb-user-profiles.md  # [DEPRECATED]
    0020-deprecate-mongodb.md      # Supersedes 0003
```

### Naming Convention

- Format: `NNNN-title-with-dashes.md`
- Sequential numbering (0001, 0002, ...)
- Lowercase, dashes between words
- Keep titles short but descriptive

---

## ADR Index (README.md)

Maintain a table of all ADRs in `docs/adr/README.md`:

```markdown
# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for [Project Name].

## Index

| ADR                                   | Title                              | Status     | Date       |
| ------------------------------------- | ---------------------------------- | ---------- | ---------- |
| [0001](0001-use-postgresql.md)        | Use PostgreSQL as Primary Database | Accepted   | 2024-01-10 |
| [0002](0002-caching-strategy.md)      | Caching Strategy with Redis        | Accepted   | 2024-01-12 |
| [0003](0003-mongodb-user-profiles.md) | MongoDB for User Profiles          | Deprecated | 2023-06-15 |
| [0020](0020-deprecate-mongodb.md)     | Deprecate MongoDB                  | Accepted   | 2024-01-15 |

## Creating a New ADR

1. Copy `template.md` to `NNNN-title-with-dashes.md`
2. Fill in the template
3. Submit PR for review
4. Update this index after approval

## ADR Status

- **Proposed**: Under discussion
- **Accepted**: Decision made, implementing
- **Deprecated**: No longer relevant
- **Superseded**: Replaced by another ADR
- **Rejected**: Considered but not adopted
```

---

## Automation (adr-tools)

```bash
# Install adr-tools
brew install adr-tools

# Initialize ADR directory
adr init docs/adr

# Create new ADR
adr new "Use PostgreSQL as Primary Database"

# Supersede an ADR
adr new -s 3 "Deprecate MongoDB in Favor of PostgreSQL"

# Generate table of contents
adr generate toc > docs/adr/README.md

# Link related ADRs
adr link 2 "Complements" 1 "Is complemented by"
```

---

## Common Mistakes

| Mistake | Why It Matters | Fix |
|---------|---------------|-----|
| Writing ADR after implementation | Decision already made, ADR becomes fiction | Write during design phase |
| Listing only one option | Looks like predetermined conclusion | Always include 2-3 real alternatives |
| Vague consequences ("may have issues") | Not actionable | Be specific: "Adds ~200ms latency to checkout" |
| Editing accepted ADRs | Loses historical record | Write new ADR that supersedes |
| No decision drivers | Hard to evaluate if context changes | List explicit criteria with priorities |
| Missing "Rejected" ADRs | Loses valuable context on what did not work | Document rejected options too |

---

## Best Practices

### Do

- **Write ADRs early** -- before implementation starts
- **Keep them short** -- 1-2 pages maximum
- **Be honest about trade-offs** -- include real cons
- **Link related decisions** -- build a decision graph
- **Update status** -- deprecate when superseded
- **Include rejected options** -- future context matters

### Do Not

- **Change accepted ADRs** -- write new ones to supersede
- **Skip context** -- future readers need background
- **Hide failures** -- rejected decisions are valuable
- **Be vague** -- specific decisions, specific consequences
- **Forget implementation** -- ADR without action is waste
