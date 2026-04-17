# User Research Framework

## Step 1: Define User Personas

### Persona Template

```markdown
## Persona: {{NAME}}

### Demographics
- **Role:** [Job title or user type]
- **Age Range:** [e.g., 25-35]
- **Tech Comfort:** [Low / Medium / High]

### Goals
1. [Primary goal]
2. [Secondary goal]
3. [Tertiary goal]

### Frustrations
1. "[Direct quote about pain point]"
2. "[Another pain point]"

### Context of Use
- **When:** [Frequency and timing]
- **Where:** [Device and environment]
- **Time Pressure:** [LOW / MEDIUM / HIGH]

### Design Implications
- What to prioritize
- What to avoid
```

### Example

```markdown
## Persona: Sarah Chen

### Demographics
- **Role:** Regional Sales Manager
- **Tech Comfort:** High — Salesforce, Slack, Excel

### Goals
1. See team KPIs at a glance without digging through reports
2. Approve discount requests quickly while mobile
3. Identify underperforming deals before end of quarter

### Frustrations
1. "I spend 30 minutes every morning pulling reports"
2. "I can't approve requests from my phone"

### Context of Use
- **When:** 3x daily (morning, after lunch, end of day)
- **Where:** Office 60%, mobile 30%, tablet 10%
- **Time Pressure:** HIGH — < 2 minutes between meetings

### Design Implications
- Mobile-first dashboard, KPIs above the fold
- One-tap approval with haptic feedback
- Don't bury critical info in sub-menus
- Don't use touch targets < 44px
```

## Step 2: Map User Journeys

### Journey Template

```markdown
## Journey: {{NAME}}

- **Persona:** [Who]
- **Goal:** [What they want]
- **Scenario:** [When/why]
- **Success Criteria:** [How they know they succeeded]

| Step | Action | Screen | Emotion | Pain Point | Opportunity |
|------|--------|--------|---------|------------|-------------|
| 1 | [Action] | [Screen] | [Emotion] | [Friction] | [Solution] |

### Key Insights
1. **Drop-off Risk:** [Step where users abandon]
2. **Low Point:** [Where frustration peaks]
3. **Quick Win:** [Easiest high-impact improvement]
```

## Step 3: Competitive Analysis

| Competitor | What Works | What's Frustrating | Steal This | Avoid This |
|------------|------------|-------------------|------------|------------|
| [Product] | [Pattern] | [Pain] | [Adopt] | [Anti-pattern] |

## Step 4: Usability Testing

### Quick Test (5 Users, 30 min each)

5 users find ~85% of usability problems.

#### Test Script

```
Introduction (2 min):
"We're testing the design, not you. There are no wrong answers.
Please think aloud as you navigate."

Warm-up (1 min):
"What do you notice first on this screen?"

Task 1: {{PRIMARY_TASK}} (5-7 min)
"Imagine [scenario]. Show me how you would [complete task]."

Observe:
- Success: Yes / No / Partial
- Time to complete: ___ seconds
- Number of errors: ___
- Points of hesitation: ___
- Verbal frustrations: "___"

Post-Test Questions (5 min):
1. What was your overall impression?
2. What was the most confusing part?
3. What did you like most?
4. If you could change ONE thing, what would it be?
5. How likely are you to use this? (1-10)
```

### SUS (System Usability Scale)

Rate 1-5 (1 = Strongly Disagree, 5 = Strongly Agree):

1. I think I would like to use this system frequently
2. I found the system unnecessarily complex
3. I thought the system was easy to use
4. I think I would need technical support to use this
5. I found the various functions well integrated
6. I thought there was too much inconsistency
7. I imagine most people would learn to use this quickly
8. I found the system very cumbersome to use
9. I felt very confident using the system
10. I needed to learn a lot before I could get going

**Scoring:**
- Odd items (1,3,5,7,9): Score = Response - 1
- Even items (2,4,6,8,10): Score = 5 - Response
- Sum all scores x 2.5 = Final SUS score (0-100)

**Interpretation:** >80 Excellent, 68-80 Good, 50-68 Needs improvement, <50 Poor
