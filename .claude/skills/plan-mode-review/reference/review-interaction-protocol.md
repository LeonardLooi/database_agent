# Review Interaction Protocol

Defines how to present findings, track decisions, manage multi-turn reviews, and generate visualizations.

---

## Structured Question Format

When presenting issues for human decision, use this exact format:

```
REVIEW QUESTIONS:
---
1. [CRITICAL] Issue title
   (A) Recommended option [RECOMMENDED]
   (B) Alternative option
   (C) Do nothing — reason

2. [HIGH] Issue title
   (A) Recommended option [RECOMMENDED]
   (B) Alternative option

3. [LOW] Auto-fix title
   -> Auto-fixing (no approval needed per Approval Scope Rules)
---
Reply like: "1A, 2A" (and optional notes)
```

### Rules

- Severity tag (CRITICAL/HIGH/MEDIUM/LOW) appears before each issue title
- Issues are numbered, options are lettered
- [RECOMMENDED] tag on the recommended option always
- LOW issues that fall under "just do it" are listed as auto-fixes, not questions
- End with the exact instruction: `Reply like: "1A, 2B" (and optional notes)`
- Present CRITICAL issues first, then HIGH, then MEDIUM, then LOW auto-fixes

### For Each Specific Issue

Provide:

1. **Severity** (CRITICAL/HIGH/MEDIUM/LOW)
2. **Problem description** — concrete, with file:line when code is available
3. **Current state diagram** (if not already shown for this section)
4. **2-3 options** including "do nothing" where reasonable
5. **Proposed state diagram** for the recommended option
6. **Per option:** implementation effort, risk, impact on other code, maintenance burden
7. **Recommended option** with rationale mapped to the user's stated preferences
8. **Approval scope:** see [plan-mode-protocol.md](plan-mode-protocol.md) for Critical/High/Low triage rules

---

## Decision Log

Maintain a running decision log updated after each section. Reprint at the start of each new turn.

### Format

```
DECISION LOG (updated after Section N):
---
Approved:   [list with IDs, e.g., 1A, 2A]
Rejected:   [list with IDs and brief reason]
Deferred:   [list with IDs and reason for deferral]
Auto-fixed: [list of LOW items applied]
---
```

### Rules

- Every decision must be recorded — including "do nothing" choices (log as Deferred with reason)
- Update after EACH section, not just at the end
- When starting a new turn, reprint the full log before continuing
- If a decision is revisited, note the change (e.g., "1A -> 1B (revised per user feedback)")

---

## Multi-Turn Continuity

When the review spans multiple messages or hits context limits:

### At the Start of Each New Turn

```
DECISIONS SO FAR:
---
Sections complete: [list]
Approved: [list]
Rejected: [list]
Deferred: [list]
Auto-fixed: [list]
Next: Section [N] — [name]
---
```

### Rules

- Do NOT re-review completed sections
- If earlier decisions are lost to context compression, say so and request a recap
- If the user returns after a break, provide the full "Decisions so far" summary unprompted

---

## Token Limit Triage

When running low on context, prioritize by severity:

| Priority | Treatment |
|----------|-----------|
| **CRITICAL issues** | Full analysis with diagrams |
| **HIGH issues** | 2-3 sentence description, recommendation, no diagram |
| **MEDIUM/LOW issues** | One-line list as auto-fixes |

### Rules

- Always complete the current section before triaging the next
- If a section must be skipped entirely, note it as `[SKIPPED — low priority, no CRITICAL items]`
- Never skip a section with CRITICAL items

---

## Visualization Requirements

For each review section, generate diagrams to make the review concrete.

### When to Generate Diagrams

- **BEFORE** discussing issues in a section: generate a **Current State** diagram
- **AFTER** proposing changes for each CRITICAL/HIGH issue: generate a **Proposed State** diagram
- **At end of section** (if multiple changes): generate a **Cumulative** diagram showing all approved changes

### Diagram Types by Section

| Section | Diagram Type |
|---------|-------------|
| Phase 0 (Self-Review) | Desired end state, approach comparisons, minimal build |
| Architecture | Component/system diagrams, dependency graphs, data flow |
| Code Quality | Module structure trees, dependency arrows, duplication mapping |
| Test Review | Coverage maps (tested vs gaps), test dependency flow |
| Performance | Request flow with timing annotations, query paths, cache layers |
| Production Readiness | Blast radius maps, rollback paths, migration sequences |

### Diagram Style

- Prefer **Mermaid** for architecture, sequence, and component diagrams (renders in most tools)
- Use **ASCII** (`+--+`, `-->`, `|`) for inline diagrams in narrow contexts
- Keep diagrams readable — aim for ~60 chars wide for ASCII
- Annotate with brief inline comments to highlight the problem or change
- Below every diagram, include a **one-line prose summary** (e.g., `Summary: PaymentService depends directly on Stripe SDK in 3 places with no abstraction layer.`)

---

## Section Pause Protocol

After each section:

1. Present all issues using the Structured Question Format
2. Wait for the user's response (e.g., "1A, 2B")
3. Update the Decision Log
4. If multiple changes approved, show the cumulative diagram
5. Ask: "Ready to move to Section [N+1] — [name]?"

Do NOT auto-advance to the next section without user acknowledgment.
