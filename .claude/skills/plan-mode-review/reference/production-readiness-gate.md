# Production Readiness Gate

Covers 7 subsections that must all pass before approving a change for implementation. This supplements Phase 1-4 (Architecture, Code Quality, Tests, Performance) with production-specific concerns.

---

## 5.1 — Blast Radius Assessment

Map every file, module, service, and data model this change touches. Identify downstream consumers.

### Process

1. List all files/modules directly modified
2. Trace imports/dependents — what calls or consumes the changed code?
3. Identify downstream consumers: other features, APIs, teams, or external services
4. Rate each affected area:

| Risk Level | Criteria | Examples |
|-----------|----------|----------|
| **Green — Low** | Isolated, no shared consumers | Internal helper, private method, test file |
| **Yellow — Medium** | Shared code, used by multiple features | Shared utility, common component, internal API |
| **Red — High** | Critical path, external consumers, data contracts | Payment flow, auth middleware, public API, DB schema |

### Output Template

```
## Blast Radius Map

### Direct Changes
- [file/module]: [what changed]

### Downstream Consumers
- [consumer]: [risk level] — [why]

### Diagram
[Mermaid or ASCII showing change at center, ripple effects outward]

Summary: [one-line prose summary of impact scope]
```

---

## 5.2 — Rollback Strategy

For every significant change, answer:

| Question | Answer |
|----------|--------|
| How do we undo this in production? | [deploy revert / feature flag / migration rollback / etc.] |
| Is this backward-compatible? | Yes/No — [migration window if no] |
| Should this be behind a feature flag? | Yes/No — [recommend if any Red blast radius items] |
| Are DB migrations reversible? | Yes/No — [safe rollback plan if no] |

### Output Template

```
## Rollback Plan

### Strategy: [deploy revert / feature flag / migration rollback]
### Steps:
1. [step]
2. [step]
3. [step]

### Diagram
[Mermaid or ASCII showing rollback sequence]
```

For database migration rollback patterns, refer to `database-schema-designer` skill reference: `migration-patterns.md`.

---

## 5.3 — Dependency Health Check

For every **new dependency** introduced (library, service, API, infrastructure):

| Check | How to Verify |
|-------|--------------|
| **Maintenance status** | Last commit date, release frequency, open issues count |
| **Bus factor** | Active maintainers count, corporate backing vs solo dev |
| **Security** | Known CVEs, audit history |
| **Size/weight** | Bundle size or build time impact |
| **Alternatives** | Lighter or more established options |

### Output Template

```
## Dependency: [name@version]

| Check | Result |
|-------|--------|
| Last release | [date] |
| Maintainers | [count] — [backed by X] |
| Known CVEs | [count or "none"] |
| Bundle impact | [size] |
| Alternatives | [list or "none better"] |

**Verdict:** SAFE / CAUTION / RECOMMEND ALTERNATIVE
```

### Verification Commands (when tooling unavailable)

```bash
# npm
npm info <pkg> time modified && npm audit

# pip
pip show <pkg> && pip-audit

# GitHub pulse
# https://github.com/<owner>/<repo>/pulse

# CVE search
# https://osv.dev/list?q=<pkg>
```

If data is unavailable, mark as `[UNVERIFIED — verify manually]` with the specific command.

---

## 5.4 — Second-Order Effects

Think 3 months ahead. Answer:

| Question | Answer |
|----------|--------|
| If we ship this, what will we be forced to change next? | [follow-on work created] |
| What assumptions does this bake in that might not age well? | [hard-coded limits, schema decisions, API contracts] |
| Does this close any doors? | [future migration, refactor, or pivot made harder] |

Rate each effect:

| Severity | Meaning |
|----------|---------|
| **Low** | Nice to know — no action needed |
| **Medium** | Plan for it — add to backlog |
| **High** | Reconsider the approach — may not be worth the constraint |

---

## 5.5 — Cost & Infrastructure Impact

| Question | Answer |
|----------|--------|
| New infrastructure required? | [new service, queue, DB, cache, third-party subscription] |
| Cloud cost estimate | [negligible / $10s / $100s / $1000s per month] |
| Operational complexity | [new monitoring, alerting, on-call considerations] |
| Scale implications | [what happens at 10x? 100x?] |

If this is a code-only change with no infra impact, state "No infrastructure impact" and skip.

---

## 5.6 — Data Migration Plan (If Applicable)

Only required when the change touches data models, schemas, or storage.

| Question | Answer |
|----------|--------|
| How do we migrate existing data? | [backfill / lazy migration / dual-write] |
| Can migration run with zero downtime? | Yes/No — [downtime window if no] |
| How do we validate data integrity? | [validation query / checksums / row counts] |
| If migration fails halfway, what state is data in? | [recoverable / corrupted / needs manual fix] |

### Output Template

```
## Data Migration Plan

### Strategy: [backfill / lazy / dual-write]
### Steps:
1. [before state]
2. [migration step]
3. [after state]

### Validation:
- [check 1]
- [check 2]

### Rollback:
- [what happens if it fails at step N]
```

If no data model changes, state "No data migration required" and skip.

---

## 5.7 — Success Metrics

Define how we know this change WORKED after deployment — not just "deployed without errors."

| Metric | Baseline (current) | Target | How to Measure | Observation Window |
|--------|-------------------|--------|----------------|-------------------|
| [e.g., checkout error rate] | [e.g., 2.3%] | [e.g., <1%] | [e.g., Datadog dashboard X] | [e.g., 7 days post-deploy] |

If no measurable metric applies (pure refactor, internal tooling), state "No success metrics — internal change" and skip.

---

## Production Readiness Gate Checklist

Before approving for implementation, ALL must be true:

```
PRODUCTION READINESS GATE:
- [ ] Blast radius is mapped and acceptable (5.1)
- [ ] Rollback strategy exists for every significant change (5.2)
- [ ] All new dependencies pass health check (5.3)
- [ ] Second-order effects identified and acceptable (5.4)
- [ ] Cost/infra impact understood (5.5)
- [ ] Data migration plan exists if applicable (5.6)
- [ ] Success metrics defined or explicitly skipped (5.7)
- [ ] Human approved the production readiness assessment
```

**If ANY item is unchecked: STOP. Do not approve. Ask for what's missing.**
