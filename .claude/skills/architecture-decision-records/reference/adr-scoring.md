# ADR Option Scoring Rubric

Use this rubric when writing a Standard MADR for a significant architecture decision. Score each considered option from two independent lenses. The scores make the reasoning behind the final decision auditable and arguable.

## The Two Lenses

Every architecture decision has two failure modes that pull in opposite directions:

- **Under-engineered**: Works today, collapses at scale. Correct on paper, nightmare to operate.
- **Over-engineered**: Solves the wrong problem. Elegant system nobody can use or maintain.

Scoring from two lenses simultaneously forces both dimensions into the open.

| Lens | Question It Answers | What It Catches |
|------|---------------------|----------------|
| **Systems Lens** | "Will this survive production?" | Complexity, failure modes, scalability ceilings, hidden coupling |
| **Developer Lens** | "Will a team actually succeed with this?" | DX friction, cognitive load, debugging difficulty, onboarding cost |

---

## Systems Lens (50 points)

| Dimension | Points | What to Evaluate |
|-----------|--------|-----------------|
| **Problem fit** | 15 | Does this directly solve the stated problem, or does it solve an adjacent problem and hope? A perfect solution to the wrong problem scores 0. |
| **Failure mode clarity** | 15 | Are the failure modes known, bounded, and recoverable? Or are they opaque and cascading? Known failures score high; unknown failures score low regardless of probability. |
| **Scale headroom** | 10 | How far does this take us before the next re-architecture? Order of magnitude = 10. 2x headroom = 3–4. |
| **Operational cost** | 10 | What does this add to deploy, monitor, debug, and on-call? More moving parts = lower score. |

**Score this lens by dimension, then sum.**

---

## Developer Lens (50 points)

| Dimension | Points | What to Evaluate |
|-----------|--------|-----------------|
| **Cognitive load** | 15 | How much does a developer need to hold in their head to work in this system? Single-concept = high score. Global state + side effects = low score. |
| **Local reasoning** | 15 | Can a change be understood and tested without tracing through 5 other services? Isolated = high. Requires reading 3 other repos to understand = low. |
| **Onboarding time** | 10 | How long before a new team member can make a safe change in this area? Days = high. Weeks = medium. "Ask the one person who knows" = low. |
| **Debugging experience** | 10 | When this breaks at 2am, how quickly can the on-call engineer locate the cause? Structured logs + single service = high. Distributed trace across 6 hops = low. |

**Score this lens by dimension, then sum.**

---

## Combined Score and Verdict

**Formula:** `(Systems score × 0.5) + (Developer score × 0.5)`

| Combined Score | Verdict | Meaning |
|----------------|---------|---------|
| 85–100 | **ADOPT** | Strong on both lenses. Move to implementation. |
| 70–84 | **ADOPT WITH MITIGATIONS** | One lens has a weak spot. State mitigations explicitly in the ADR before accepting. |
| 55–69 | **REVISIT** | Meaningful weakness on at least one lens. Re-evaluate options or redesign the weak dimension. |
| < 55 | **REJECT** | Fails on a fundamental dimension. Do not proceed without a substantially different approach. |

---

## Lens Gap Rule

**If the two lens scores differ by more than 20 points, the gap is the finding — not the combined score.**

Do not average away a 20-point gap. Name the failing lens and address that dimension specifically before proceeding.

Common gap patterns and what they mean:

| Pattern | Diagnosis |
|---------|-----------|
| Systems high / Developer low | Technically correct but will destroy team velocity. Microservices trap. |
| Developer high / Systems low | Nice to work with but built on a time bomb. Polling instead of events. |
| Both low | Wrong problem entirely. Re-examine the context section of the ADR. |
| Both high, differ by ≤10 | Genuinely good decision. Score difference is noise. |

---

## Worked Example

**Decision:** Internal service communication protocol — REST vs gRPC

### Option 1: REST (JSON over HTTP/1.1)

**Systems Lens:**
- Problem fit: 13/15 — solves the problem directly; REST is proven for this scale
- Failure mode clarity: 13/15 — HTTP status codes, timeouts well understood
- Scale headroom: 7/10 — sufficient to 10x current load; may need upgrade beyond that
- Operational cost: 9/10 — standard tooling, every engineer knows it

Systems total: **42/50**

**Developer Lens:**
- Cognitive load: 14/15 — every developer already knows HTTP semantics
- Local reasoning: 13/15 — curl-testable, Postman-debuggable, no special tooling
- Onboarding time: 14/10 → cap at 10/10 — zero ramp-up
- Debugging experience: 13/10 → cap at 10/10 — HTTP logs readable in plain text

Developer total: **47/50**

Combined: **(42 × 0.5) + (47 × 0.5) = 44.5 → 89/100**
Verdict: **ADOPT**

---

### Option 2: gRPC (Protocol Buffers over HTTP/2)

**Systems Lens:**
- Problem fit: 12/15 — solves the problem; adds streaming capability we don't currently need
- Failure mode clarity: 10/15 — error codes less universal; HTTP/2 multiplexing failures harder to diagnose
- Scale headroom: 10/10 — binary protocol, streaming, bidirectional; significant headroom
- Operational cost: 6/10 — requires proto compilation step, separate toolchain

Systems total: **38/50**

**Developer Lens:**
- Cognitive load: 9/15 — proto schema + generated code + HTTP/2 semantics = three things to know
- Local reasoning: 8/15 — cannot curl-test; requires grpcurl or generated client; harder to inspect in transit
- Onboarding time: 7/10 — proto toolchain setup takes a day; schema-first requires discipline
- Debugging experience: 6/10 — binary on the wire; requires tooling to decode; harder in production

Developer total: **30/50**

Combined: **(38 × 0.5) + (30 × 0.5) = 34 → 68/100**
Lens gap: 38 − 30 = **8 points** (within threshold)
Verdict: **REVISIT** — Developer lens is the weak side. If the team has existing gRPC experience, re-score Developer; otherwise REST is the better choice for current context.

---

## When to Use This Rubric

**Use it for:** Standard MADR decisions — significant architecture choices, technology selections, pattern adoption, cross-service contracts.

**Skip it for:** Y-Statement decisions (simple tech selection), Lightweight ADRs (medium complexity where the trade-off is already clear), Deprecation ADRs (the decision is already made; scoring is retrospective noise).

**Scoring is qualitative judgment made explicit, not a formula from a tool.** Two engineers scoring the same option may differ by 5–8 points on a dimension. That's fine. The value is in the conversation the scores create, not the numbers themselves.
