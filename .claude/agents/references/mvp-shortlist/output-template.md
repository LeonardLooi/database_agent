# MVP Shortlist Output Template & Reference

This file contains the output templates, screen mapping guides, business model metrics, example structures, and quality checklist for the MVP Shortlist Agent. Loaded on-demand by the agent.

---

## Screen Mapping for Wireframes

### Screen Derivation Rules

| Feature Type | Typical Screens |
|--------------|-----------------|
| **Authentication** | Login, Signup, Forgot Password (often 1 combined) |
| **Dashboard/Overview** | 1 screen per user role |
| **CRUD Entity** | List view + Detail/Edit view (2 screens) |
| **Workflow/Process** | 1 screen per major step |
| **Settings/Config** | 1 screen (can combine multiple) |
| **Communication** | Inbox/Thread view (1-2 screens) |

### Screen Budget Formula
```
Screens = (Distinct Features / 2) + (User Roles x 2)

Example: 12 features, 2 user roles
Screens = (12 / 2) + (2 x 2) = 6 + 4 = 10 screens
```

### Experience Architecture per Screen

For each screen, define not just WHAT it contains but HOW it feels:

```markdown
| Screen # | Screen Name | User | Features Covered | Key Components | Interactions | Emotion at Entry | Emotion at Exit |
|----------|-------------|------|------------------|----------------|--------------|------------------|-----------------|
| T1 | Tenant Login | Tenant | F29 | Email/phone input, SSO buttons | Auth flow | [Neutral/Anxious] | [Confident] |
| T2 | Tenant Dashboard | Tenant | F12, F30 | Stat cards, ticket list, activity feed | Tap to detail | [Curious] | [In-control] |
| L1 | Landlord Setup | Landlord | F20 | Wizard steps, progress indicator | Next/Back | [Uncertain] | [Capable] |
...
```

### First 60 Seconds — Scripted Experience

Script the first minute like a movie scene. The wireframe agent needs this to design the right feel, not just the right layout.

```markdown
| Second | User Does | System Responds | Physics Value | Emotional Value |
|--------|-----------|-----------------|---------------|-----------------|
| 0-10 | [Opens app] | [What greets them] | [Speed/simplicity] | [First feeling] |
| 10-25 | [First action] | [Response] | [Capability shown] | [Feeling shifts to] |
| 25-45 | [Core action] | [Magic happens] | [10x moment] | [Wow moment] |
| 45-60 | [Sees result] | [Confirmation] | [Value delivered] | [Emotional payoff] |
```

### Primary Flow — One Path, Maximum 5 Steps

```markdown
[TRIGGER] -> [STEP 1] -> [STEP 2] -> [STEP 3] -> [VALUE]
     |            |            |            |           |
 Physics:   [Efficient]  [Powerful]    [10x]     [Delivered]
 Feeling:   [Intrigued]  [Capable]     [Wow]     [Proud]
```

If the primary flow has more than 5 steps, simplify until it doesn't.

### Invisible Details (Wireframe Agent Guidance)

| State | Standard Approach | Designed Approach | Why Better |
|-------|-------------------|-------------------|------------|
| Loading | Spinner | [Your approach] | [Faster/Smarter feel] |
| Empty | Blank page | [Your approach] | [Helpful/Inviting] |
| Error | Red text | [Your approach] | [Helpful/Human] |
| Success | Checkmark | [Your approach] | [Celebratory/Satisfying] |
| Edge case | Broken | [Your approach] | [Graceful] |

---

## Death Scenarios

It's 18 months from now. The product is dead. What killed it?

```markdown
| Death Scenario | Probability | Warning Signs NOW | Test THIS WEEK | Kill Trigger |
|----------------|-------------|-------------------|----------------|--------------|
| [Cause 1] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |
| [Cause 2] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |
| [Cause 3] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |
```

**The #1 Threat:** [Most likely killer]
**Test Immediately:** [Experiment to validate or kill this threat]

---

## Kill Criteria — Success Metrics by Business Model

Define BEFORE building. If metrics aren't met after 30 days of active effort, act on the kill trigger.

### SaaS Metrics
| Metric | Good | Great | Kill If Below |
|--------|------|-------|---------------|
| Activation (reach aha moment) | 30% | 50%+ | 15% |
| Trial -> Paid | 5% | 15%+ | 2% |
| 30-Day Retention | 70% | 85%+ | 40% |
| Month-1 Revenue | $1K | $5K+ | $0 |

### Marketplace Metrics
| Metric | Good | Great | Kill If Below |
|--------|------|-------|---------------|
| Supply signup | 20%+ | 40%+ | 10% |
| Demand conversion | 5% | 15%+ | 2% |
| Repeat transaction | 30% | 50%+ | 15% |
| Take rate achieved | 8% | 15%+ | 3% |

### Consumer App Metrics
| Metric | Good | Great | Kill If Below |
|--------|------|-------|---------------|
| D1 Retention | 30% | 50%+ | 15% |
| D7 Retention | 15% | 25%+ | 5% |
| D30 Retention | 8% | 15%+ | 3% |
| Paid conversion | 2% | 5%+ | 0.5% |

**Your Kill Criteria:** "If [METRIC] < [THRESHOLD] after 30 days of active effort, we [PIVOT/KILL]."

---

## Output Format: MVP Shortlist

```markdown
# [PRODUCT NAME] -- MVP Shortlist

## Product Soul

- **The One Function:** [Core capability at physics level]
- **The One Feeling:** [Core emotional payoff]
- **The One Moment:** [Where physics and feeling collide]
- **The Enemy:** [Carried forward from backlog]
- **The Human Truth:** [Carried forward from backlog]
- **The One Line:** [Carried forward from backlog]

---

## Executive Summary

**Original Backlog:** [N] features across [M] modules
**MVP Selected:** [X] features ([Y]% of backlog)
**Revenue Model:** [How this MVP leads to payment]
**Kill Criteria:** "If [METRIC] < [THRESHOLD] after 30 days, we [ACTION]"

---

## Titan Evaluation Summary

### Top Scoring Features
| Rank | Feature ID | Feature Name | Elon Score | Jobs Score | Combined | Revenue Path | MVP? |
|------|------------|--------------|------------|------------|----------|--------------|------|
| 1 | F1 | [Name] | [X]/10 | [X]/10 | [X]/10 | [Direct/Path/Support] | Y/N |
| 2 | F3 | [Name] | [X]/10 | [X]/10 | [X]/10 | [Direct/Path/Support] | Y/N |
...

### The Subtraction Verdict
| Feature ID | Serves Function? | Serves Feeling? | Revenue Path? | Complexity? | Launch Without? | VERDICT |
|------------|-----------------|-----------------|---------------|-------------|-----------------|---------|
| F1 | [Y/N] | [Y/N] | [Y/N] | [Y/N] | [Y/N] | KEEP/DEFER/DELETE |
...

### Features Deferred (v1.1+)
| Feature ID | Feature Name | Reason Deferred | Trigger to Add |
|------------|--------------|-----------------|----------------|
| F7 | [Name] | [Low urgency/High effort/Not on revenue path] | [When to reconsider] |
...

### Features Deleted
| Feature ID | Feature Name | Why Deleted |
|------------|--------------|-------------|
| F15 | [Name] | [MVP Killer / Doesn't serve soul / No revenue path / Peripheral] |
...

---

## The "NOT Building" List

What we are DELIBERATELY not building and why. The length of this list indicates focus.

| Feature | Why It's Tempting | Why We're Saying No | Reconsider When |
|---------|-------------------|---------------------|-----------------|
| [Feature/Capability] | [Appeal] | [Focus reason] | [Trigger] |
...

**Common MVP Killers Rejected:**
- [x] No admin dashboard -- using [alternative]
- [x] No team features -- single-player first
- [x] Single auth method -- [which one]
- [Other items from the anti-pattern list that were cut]

---

## Kill List

> **Philosophy:** The Kill List prevents feature creep by making exclusions explicit and documented. Every feature not in the MVP must be accounted for — either deferred with a trigger, flagged for validation, or killed with a reason. This discipline ensures nothing silently creeps back in without re-evaluation. The Kill List also provides a ready-made v2 roadmap from the "Deferred" category and a validation backlog from the "Needs Validation" category.
>
> As Elon says: *"If you're not sure, remove it. You can always add it back."*

### Kill List Summary

| Feature ID | Feature Name | Score | Category | Reason |
|------------|-------------|-------|----------|--------|
| F__ | [Name] | [X]/10 | Deferred to v2 | [Useful but not launch-critical — e.g., "Good feature, not on critical path to revenue"] |
| F__ | [Name] | [X]/10 | Deferred to v2 | [e.g., "Enhances experience but core works without it"] |
| F__ | [Name] | [X]/10 | Needs Validation | [Uncertain value — e.g., "Assumption untested, needs user research first"] |
| F__ | [Name] | [X]/10 | Needs Validation | [e.g., "Users say they want it but no behavioral evidence"] |
| F__ | [Name] | [X]/10 | Killed | [Should NOT be built — e.g., "Distraction from core value prop"] |
| F__ | [Name] | [X]/10 | Killed | [e.g., "Adds complexity without proportional value, violates first principles"] |
...

### Category Definitions

| Category | Meaning | Action |
|----------|---------|--------|
| **Deferred to v2** | Good features that don't make the MVP cut. They serve the product soul but aren't essential for launch or the initial revenue path. | Add to v2 roadmap. Revisit after MVP metrics are validated. |
| **Needs Validation** | Features with uncertain value that need user testing, behavioral evidence, or market validation before committing engineering effort. | Design validation experiments. Build only after evidence confirms demand. |
| **Killed** | Features that should NOT be built — they violate first principles, add complexity without proportional value, distract from the core, or are solutions looking for a problem. | Do not build. Do not reconsider unless the product thesis fundamentally changes. |

### Kill List Audit

After populating the Kill List, verify:
- [ ] Every non-MVP feature from the backlog appears in exactly one category
- [ ] "Deferred" features have a specific trigger for reconsideration (metric, user count, or revenue milestone)
- [ ] "Needs Validation" features have a linked experiment (from Validation Experiments section)
- [ ] "Killed" features have a one-line reason rooted in first principles, not opinion
- [ ] The Kill List is at least as long as the MVP feature list (if not, you haven't been ruthless enough)

---

## MVP Options Comparison

| Criteria | Option 1: [Name] | Option 2: [Name] | Option 3: [Name] |
|----------|------------------|------------------|------------------|
| Feature Count | [N] | [N] | [N] |
| Physics Score | [X]/10 | [X]/10 | [X]/10 |
| Taste Score | [X]/10 | [X]/10 | [X]/10 |
| Revenue Path | [Clear/Indirect/Unclear] | [Clear/Indirect/Unclear] | [Clear/Indirect/Unclear] |
| Moat Seed | [Type] | [Type] | [Type] |
| Risk Level | [Low/Med/High] | [Low/Med/High] | [Low/Med/High] |

**Recommended:** Option [N] -- [Name]
**Reason:** [2-3 sentence justification using Titan reasoning — must reference physics, taste, AND revenue path]

---

## Selected MVP: [Option Name]

### Feature List
| Feature ID | Module | Feature Name | End User | Category | AI Level | Revenue Role |
|------------|--------|--------------|----------|----------|----------|--------------|
| F1 | [Module] | [Name] | [User] | [Core/Diff] | [None/Assist/Auto] | [Direct/Path/Support] |
...

### Revenue Path
```
[Feature A] -> [Feature B] -> [Feature C] -> PAYMENT MOMENT -> [Retention Feature]
```

### Moat Seed
**Type:** [Data network effects / Switching costs / Brand love / Ecosystem lock-in]
**Feature:** [Which MVP feature begins building this moat]
**How It Compounds:** [How usage makes defensibility stronger over time]

### Dependency Graph
```
F29 (Auth) --> F30 (Dashboard)
                   |
         +---------+---------+
         v                   v
    F1 (Report)       F12 (Status Hub)
         |                   |
         v                   v
    F3 (Schedule)     F13 (AI Summary)
         |
         v
    F4 (Proof Timeline)
```

### User Flows

**Tenant Flow:**
```
Login (F29) -> Dashboard (F30) -> Report Issue (F1) -> AI Triage ->
Schedule (F3) -> Live ETA -> Proof Timeline (F4)
```

**Landlord Flow:**
```
Setup Wizard (F20) -> Dashboard (F30) -> Triage Queue ->
Assign Vendor (F3) -> Approvals (F10) -> Proof Export (F4)
```

---

## Screen Requirements for Wireframing

### First 60 Seconds (Scripted Experience)
| Second | User Does | System Responds | Physics Value | Emotional Value |
|--------|-----------|-----------------|---------------|-----------------|
| 0-10 | [Action] | [Response] | [Value] | [Feeling] |
| 10-25 | [Action] | [Response] | [Value] | [Feeling] |
| 25-45 | [Action] | [Response] | [Value] | [Feeling] |
| 45-60 | [Action] | [Response] | [Value] | [Feeling] |

### Primary Flow
```
[TRIGGER] -> [STEP 1] -> [STEP 2] -> [STEP 3] -> [VALUE]
     |            |            |            |           |
 Physics:   [Efficient]  [Powerful]    [10x]     [Delivered]
 Feeling:   [Intrigued]  [Capable]     [Wow]     [Proud]
```

### Tenant Screens ([N] total)
| # | Screen Name | Features | Key Components | Nav Position | Emotion Entry -> Exit |
|---|-------------|----------|----------------|--------------|----------------------|
| T1 | Login | F29 | Email/phone, SSO | - | Neutral -> Confident |
| T2 | Dashboard | F12, F30 | Stats, tickets, feed | Home | Curious -> In-control |
| T3 | Report Issue | F1 | Voice btn, photo grid, room select | Report | Frustrated -> Hopeful |
...

### Landlord Screens ([N] total)
| # | Screen Name | Features | Key Components | Nav Position | Emotion Entry -> Exit |
|---|-------------|----------|----------------|--------------|----------------------|
| L1 | Setup Wizard | F20 | Steps, progress | - | Uncertain -> Capable |
| L2 | Portfolio | F30 | Property cards, stats | Home | Overwhelmed -> Organized |
| L3 | Triage Queue | F1, F12 | Ticket cards, filters | Tickets | Reactive -> Proactive |
...

### Shared Components
| Component | Used In | Behavior |
|-----------|---------|----------|
| Status Pill | T2, L3 | Color-coded status indicator |
| Ticket Card | T2, L3, L4 | Expandable ticket summary |
| Timeline | T7, L8 | Vertical event history |
...

### Invisible Details (Wireframe Agent Guidance)
| State | Designed Approach | Feeling |
|-------|-------------------|---------|
| Loading | [Approach] | [Not-waiting] |
| Empty | [Approach] | [Invited-to-act] |
| Error | [Approach] | [Guided-not-blamed] |
| Success | [Approach] | [Celebrated] |

---

## Build Plan

### Week 1: Foundation + Revenue Path
| Day | Tasks | Features | Revenue Impact |
|-----|-------|----------|----------------|
| 1-2 | Auth + basic routing | F29 | Prerequisite |
| 3-4 | Dashboard shells (T2, L2) | F30 | User sees value |
| 5 | Report issue flow | F1 | Core value delivery |

### Week 2: Core Flows
| Day | Tasks | Features | Revenue Impact |
|-----|-------|----------|----------------|
| 1-2 | Scheduling flow | F3 | Core value delivery |
| 3-4 | Proof timeline | F4 | Retention trigger |
| 5 | Status hub | F12 | Engagement |

### Week 3: Polish + AI
| Day | Tasks | Features | Revenue Impact |
|-----|-------|----------|----------------|
| 1-2 | AI triage integration | F1 (AI) | 10x / Wow moment |
| 3-4 | Thread summary | F13 | Differentiation |
| 5 | Approval rules | F10 | Trust building |

### Week 4: Launch Prep
| Day | Tasks | Features | Revenue Impact |
|-----|-------|----------|----------------|
| 1-2 | Bug fixes, edge cases | All | Quality |
| 3 | QA + user testing | - | Validation |
| 4 | Final polish | - | Taste |
| 5 | **LAUNCH** | - | Revenue begins |

---

## Death Scenarios (Output Section)

| Death Scenario | Probability | Warning Signs NOW | Test THIS WEEK | Kill Trigger |
|----------------|-------------|-------------------|----------------|--------------|
| [Cause 1] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |
| [Cause 2] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |
| [Cause 3] | [H/M/L] | [Signs] | [Experiment] | "If X, we pivot" |

**#1 Threat:** [Most likely killer]
**Test Immediately:** [Experiment]

---

## Kill Criteria (Output Section)

**Business Model:** [SaaS / Marketplace / Consumer App]

| Metric | Target | Kill If Below | Measurement Method |
|--------|--------|---------------|-------------------|
| [Metric 1] | [Good] | [Threshold] | [How to measure] |
| [Metric 2] | [Good] | [Threshold] | [How to measure] |
| [Metric 3] | [Good] | [Threshold] | [How to measure] |

**Kill Trigger:** "If [PRIMARY METRIC] < [THRESHOLD] after 30 days of active effort, we [PIVOT/KILL]."

---

## Validation Experiments

Before building, validate these assumptions:

| # | Assumption | Experiment | Success Metric | Failure Action |
|---|------------|------------|----------------|----------------|
| 1 | [Assumption] | [Test method] | [What success looks like] | [Pivot/Redesign/Kill] |
| 2 | [Assumption] | [Test method] | [What success looks like] | [Pivot/Redesign/Kill] |
| 3 | [Assumption] | [Test method] | [What success looks like] | [Pivot/Redesign/Kill] |

---

## Titan Verdict

**Physics Score:** [X]/10
> [Elon's perspective: Is this 10x? What are the constraints? Can we ship fast? Is there a revenue path?]

**Taste Score:** [X]/10
> [Jobs' perspective: Is this insanely great? Where's the wow? Is it simple enough? Does it have a soul?]

**Combined Score:** [X]/10

**Confidence Level:** [HIGH / MEDIUM / LOW]
*Based on: [Quality of backlog data, strength of behavioral evidence, founder context]*

**Verdict:** [BUILD IT / REFINE IT / RETHINK]

**The Unfiltered Truth:**
> [3-4 sentences of honest Titan assessment. What would Elon cut? What would Jobs polish? Is this MVP coherent or a feature soup? Does it have a clear revenue path or is it a hope-based business? Does it fight the Enemy or just add noise?]

---

## Handoff to Wireframe Agent

Ready for wireframing. Invoke the premium wireframe agent with:

**Project:** [Product Name]
**MVP Option:** [Selected option name]
**Screens:** [Total count] ([Tenant count] Tenant + [Landlord count] Landlord)
**Features:** [Comma-separated list of Feature IDs]
**Style:** Premium 2026 Dual-Theme
**Product Soul:** [One function + One feeling + One moment]
**First 60 Seconds:** [Scripted experience reference]
**Primary Flow:** [Step 1 -> Step 2 -> ... -> Value]
**Invisible Details:** [Loading/Empty/Error/Success approaches]

Screen specifications and experience architecture above define the wireframe requirements.
```

---

## Quality Checklist

Before delivering MVP shortlist:

- [ ] Product Soul defined (one function + one feeling + one moment)
- [ ] All features scored with Titan criteria (both lenses)
- [ ] Subtraction Game applied to every feature with documented verdicts
- [ ] Common MVP Killers checked — none included without explicit justification
- [ ] Revenue path mapped with payment trigger identified
- [ ] MVP includes at least one Revenue-Direct or Revenue-Path feature
- [ ] "NOT Building" list is populated and substantive (short list = weak focus)
- [ ] Kill List is complete — every non-MVP feature categorized as Deferred to v2, Needs Validation, or Killed
- [ ] Kill List is at least as long as the MVP feature list
- [ ] Every "Deferred" feature has a specific reconsideration trigger
- [ ] Every "Needs Validation" feature links to a validation experiment
- [ ] Every "Killed" feature has a first-principles reason (not opinion)
- [ ] Dependency graph is complete and accurate
- [ ] MVP options are distinct (not just "more/less features") with different souls/wedges
- [ ] Selected MVP has clear rationale referencing physics, taste, AND revenue
- [ ] Moat seed identified (which feature begins building defensibility)
- [ ] Screen count is reasonable (10-20 for mobile)
- [ ] First 60 seconds scripted with physics and emotional values
- [ ] Primary flow has maximum 5 steps
- [ ] Emotional entry/exit defined for each screen
- [ ] Invisible details defined (loading, empty, error, success states)
- [ ] User flows cover primary use cases
- [ ] Death scenarios identified with test-this-week experiments
- [ ] Kill criteria defined with specific thresholds and business model context
- [ ] Validation experiments have failure actions (not just success metrics)
- [ ] Build timeline maps features to revenue impact
- [ ] Wireframe handoff includes experience architecture (not just components)
- [ ] Titan Verdict includes confidence level
