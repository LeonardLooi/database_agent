# Idea-to-Backlog Output Template & Reference

This file contains the output template, example, and quality checklist for the idea-to-backlog agent. It is loaded on-demand during backlog generation.

---

## Output Format: Feature Backlog

Generate a comprehensive backlog in this exact structure:

```markdown
# [PRODUCT NAME] Feature Backlog

## Product Soul

- **The Enemy:** [The force this product fights — not a competitor]
- **The Human Truth:** [The fundamental insight about being human this addresses]
- **The One Line:** [Simple, true, memorable — the "1,000 songs in your pocket"]

---

## Executive Summary

- **One-Line Idea:** [Original input]
- **Target Users:** [Primary, Secondary — with specificity]
- **Core Problem:** [The #1 pain point with behavioral evidence]
- **10x Opportunity:** [Where you're 10x better and WHY based on physics]
- **Wow Moment:** [The specific moment when eyes go wide]
- **Revenue Path:** [How this leads to users paying]

---

## Pain Points Summary (Validated)

| # | Pain Point | Evidence Source | Quote | User Type | Severity | Emotion Felt | Behavior Evidence | Validated? |
|---|------------|-----------------|-------|-----------|----------|--------------|-------------------|------------|
| P1 | [Problem] | [Source] | "[Quote]" | [Who] | [1-5] | [Emotion] | [Money/time/workaround] | [Y/N] |
| P2 | [Problem] | [Source] | "[Quote]" | [Who] | [1-5] | [Emotion] | [Money/time/workaround] | [Y/N] |
...

---

## Root Cause Analysis (Five Whys)

### Pain Point: [P1 — Top pain point]
Why? -> [Why 1] -> [Why 2] -> [Why 3] -> [Why 4] -> **ROOT: [Why 5]**

### Pain Point: [P2 — Second pain point]
Why? -> [Why 1] -> [Why 2] -> [Why 3] -> [Why 4] -> **ROOT: [Why 5]**

### Pain Point: [P3 — Third pain point]
Why? -> [Why 1] -> [Why 2] -> [Why 3] -> [Why 4] -> **ROOT: [Why 5]**

**Root Insights:** [What these root causes reveal about the real problem]

---

## "Impossible" Opportunities

| What People Assume | Category | Opportunity Level |
|--------------------|----------|-------------------|
| [Assumed impossible thing] | Real / Fake / Lazy Impossible | [None / HIGH / MEDIUM] |
...

Features targeting "Fake impossible" items are marked with * in the backlog.

---

## Competitive Landscape

| Competitor | URL | Strengths | Weaknesses | User Quote | Your Advantage |
|------------|-----|-----------|------------|------------|----------------|
| [Name] | [URL] | [What works] | [What's broken] | "[From reviews]" | [Your edge] |
...

---

## Assumption Risk Register

| # | Assumption | Evidence For | Evidence Against | If Wrong = | Status |
|---|------------|--------------|------------------|------------|--------|
| A1 | [Assumption] | [Evidence] | [Counter] | [Kill/Hurt/Minor] | [Valid/Risky/Unvalidated] |
...

**#1 Death Threat:** [Most likely way this fails]
**Kill Test:** [How to validate or kill with <$100 and <10 hours]

---

## Market Sizing (TAM/SAM/SOM)

| Level | Estimate | Basis |
|-------|----------|-------|
| **TAM** | $[X]B | [Global market for the problem domain] |
| **SAM** | $[X]B | [Segment reachable by this product model] |
| **SOM** | $[X]M | [Year 1 realistic target with early adopters] |

[One sentence on whether the market is large enough to justify building.]

---

## Feature Backlog

| Feature ID | Module | Feature Name | One-line Summary | End User | Pain Point | Fights Enemy? | User Story | Category | Comp/Competitive | Revenue Proximity | MVP? | AI Level | AI Capability | Data Needed | Integrations | Existing Players | Notes |
|------------|--------|--------------|------------------|----------|------------|---------------|------------|----------|------------------|-------------------|------|----------|---------------|-------------|--------------|------------------|-------|
| F1 | [Module] | [Name] | [Summary] | [User] | [P#] | [Direct/Indirect/No] | As a [user], I want [action] so that [benefit] | [Core/Diff/Nice] | [Comp/Competitive/Mixed] | [Direct/Path/Support/Peripheral] | [TBD] | [None/Assist/Auto/Autonomous] | [What AI does] | [Required data] | [External systems] | [Competitors] | [Extra context] |
| F2* | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |
...

(* = Addresses "Fake impossible" opportunity)

---

## Module Summary

| Module | Feature Count | Core | Differentiator | Nice-to-Have | Revenue-Path Features |
|--------|---------------|------|----------------|--------------|----------------------|
| [Module 1] | [N] | [N] | [N] | [N] | [N] |
| [Module 2] | [N] | [N] | [N] | [N] | [N] |
...

---

## Emotional Journey Map

| Touchpoint | Current Emotion | Designed Emotion | Feature That Delivers |
|------------|-----------------|------------------|----------------------|
| First open | [Overwhelmed?] | [Excited?] | [F#] |
| Core task | [Frustrated?] | [Empowered?] | [F#] |
| Completion | [Relief?] | [Pride?] | [F#] |
| Sharing | [Embarrassed?] | [Proud?] | [F#] |

---

## Recommended MVP Candidates

Based on Titan analysis (Physics + Taste), these features are MVP candidates:

| Feature ID | Why MVP | 10x Claim | Wow Moment | Revenue Path | Fights Enemy |
|------------|---------|-----------|------------|--------------|--------------|
| [F1] | [Rationale] | [Physics improvement] | [Experience magic] | [Direct/Path] | [How] |
...

---

## Next Steps

1. **Validate #1 Death Threat:** [Specific experiment with success/failure criteria]
2. **Test Unvalidated Assumptions:** [Which assumptions to test and how]
3. **User Interviews:** [Who to talk to, what to ask — focus on behavior, not opinions]
4. **Prototype Focus:** [Which features to prototype first — prioritize "Fake impossible" items]
5. **Kill Test:** [How to invalidate the core hypothesis fast — what result means kill vs. proceed]

---

## Conviction Score

### Elon's Conviction (Physics + Scale)

| Dimension | Score (/10) | Rationale |
|-----------|-------------|-----------|
| **Problem Severity** — How painful is this? | [X] | [Why] |
| **Solution Clarity** — How clear is the solution path? | [X] | [Why] |
| **Market Size** — Is the market big enough? | [X] | [Why] |

**Elon Conviction** = ([Problem] x [Solution] x [Market]) / 100 = **[X.X] /10**

### Steve's Conviction (Experience + Taste)

| Dimension | Score (/10) | Rationale |
|-----------|-------------|-----------|
| **Experience Potential** — Can this be delightful? | [X] | [Why] |
| **Story Coherence** — Does the product tell a clear story? | [X] | [Why] |
| **Delight Factor** — Will users tell friends? | [X] | [Why] |

**Steve Conviction** = ([Experience] x [Story] x [Delight]) / 100 = **[X.X] /10**

### Combined Conviction

**Combined Score** = (Elon [X.X] x 0.5) + (Steve [X.X] x 0.5) = **[X.X] /10**

| Score | Verdict | Action |
|-------|---------|--------|
| 8.0+ | **HIGH CONVICTION** | Proceed to MVP shortlisting immediately |
| 6.0-7.9 | **MODERATE** | Refine pain points or pivot angle before continuing |
| < 6.0 | **LOW CONVICTION** | Reconsider the idea or explore adjacent problems |

**VERDICT: [HIGH CONVICTION / MODERATE / LOW CONVICTION]**
**Recommendation:** [One sentence on what to do next based on the score]
```

---

## Example Input/Output

### Input:
```
"Pet care app for busy pet owners"
```

### Output Summary:
```
## Product Soul
- **Enemy:** "Scattered pet care information that forces owners to juggle apps, calendars, and memory — making them feel like negligent parents when they forget"
- **Human Truth:** "Pet owners see their pets as family, and every missed appointment or forgotten medication triggers real guilt"
- **One Line:** "Your pet's health, always handled"

## Pain Points Found (Reddit r/dogs, r/cats, r/pets):
- P1: "I always forget my dog's vet appointments" (Severity 5, Validated: users set 3+ calendar reminders)
- P2: "Tracking medications is a nightmare" (Severity 5, Validated: users build spreadsheets)
- P3: "Finding a reliable pet sitter last minute is impossible" (Severity 3, Stated only — no workaround spend found)
...

## Five Whys on P1 (Forgetting vet appointments):
Why? -> Multiple pets have different schedules
  -> No single system tracks all pet health
    -> Existing apps are pet-specific, not health-specific
      -> Pet apps prioritize social features over health management
        -> ROOT: The industry optimizes for engagement, not for the owner's peace of mind

## "Impossible" Opportunities:
- "AI can't predict when a pet needs a vet visit" -> FAKE IMPOSSIBLE (behavior patterns + breed data make this feasible)
- "You can't replace a vet's judgment" -> REAL IMPOSSIBLE (but you can surface signals that prompt the visit)

## Market Sizing:
TAM: $320B (global pet care industry)
SAM: $12B (US digital pet health and wellness platforms)
SOM: $40M (early adopter pet owners in top 10 US metros, Year 1)

## Features Generated: 32
- Core: 12 (Login, Pet profiles, Reminders, etc.)
- Differentiator: 14 (AI health predictions*, Smart sitter matching, etc.)
- Nice-to-Have: 6 (Social features, Badges, etc.)
(* = Addresses Fake impossible)

## MVP Candidates: 10 features
- F1: Pet Profile (Core, Revenue-Path)
- F3: Smart Reminder System (Differentiator, Revenue-Path — 10x better than calendar)
- F7: Vet Visit Logger (Core, Revenue-Support)
...

## Conviction Score:
Elon: Problem 9 x Solution 8 x Market 9 = 648/100 = 6.5
Steve: Experience 9 x Story 9 x Delight 8 = 648/100 = 6.5
Combined: (6.5 x 0.5) + (6.5 x 0.5) = **6.5 /10**
VERDICT: MODERATE — Strong pain points and emotional resonance, but solution path for AI health prediction needs validation. Recommend sharpening the core differentiator before MVP shortlisting.
```

---

## Quality Checklist

Before delivering backlog:

- [ ] Enemy is named (a force, not a competitor)
- [ ] Human Truth is identified (human insight, not product feature)
- [ ] One Line is crafted (simple, true, memorable)
- [ ] All pain points have evidence (quotes, sources)
- [ ] Top pain points have behavioral evidence (money/time/workarounds), not just stated preference
- [ ] Five Whys applied to top 3 pain points with root causes identified
- [ ] "Impossible" Audit completed (Real vs. Fake vs. Lazy)
- [ ] Assumption Risk Register is populated with kill/hurt/minor ratings
- [ ] #1 Death Threat identified with test-this-week experiment
- [ ] TAM/SAM/SOM market sizing included with directional estimates and justification
- [ ] SOM concern flagged if < $10M
- [ ] Every feature maps to a validated pain point
- [ ] Every feature tested against the Enemy
- [ ] Revenue Proximity assigned to every feature
- [ ] User stories follow "As a [user], I want [action] so that [benefit]"
- [ ] Emotional journey mapped (current vs. designed emotions)
- [ ] AI levels are realistic (not everything needs AI)
- [ ] Complementary/Competitive classification is justified
- [ ] MVP candidates include Revenue-Direct or Revenue-Path features
- [ ] Feature IDs are sequential (F1, F2, F3...)
- [ ] Modules group related features logically
- [ ] Competitor URLs are included where known
- [ ] Integration dependencies are identified
- [ ] "Fake impossible" features are flagged with asterisk
- [ ] Conviction Score calculated with all 6 dimensions scored and justified
- [ ] Conviction verdict (HIGH/MODERATE/LOW) stated with actionable recommendation
