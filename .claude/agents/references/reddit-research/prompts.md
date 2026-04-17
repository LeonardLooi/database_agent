# Reddit Research — Analysis Prompts

These prompts guide the agent's analysis of fetched Reddit thread data.

## Per-Thread Analysis Framework

When analyzing each thread file, extract findings into these categories:

### 1. Core Problems
- **problem**: Description of the problem people are trying to solve
- **evidence**: Paraphrased comments supporting this
- **frequency**: How many commenters mention this (count)
- **severity**: low / medium / high based on language intensity

### 2. Solution Gaps
- **current_solution**: What they're using now
- **gap**: What's missing or broken
- **impact**: How this gap affects their workflow

### 3. Workarounds
- **workaround**: Description of what they're doing
- **tools_involved**: List of tools being cobbled together
- **complexity**: simple / moderate / complex
- **pain_level**: 1-5 scale

### 4. Willingness to Pay
- **signal**: The language or context indicating purchase intent
- **strength**: weak / moderate / strong

### 5. Repeated Frustrations
- **frustration**: Description
- **count**: Number of unique commenters mentioning it
- **existing_solutions_tried**: What they've already tried

### 6. Non-Obvious Insights
- **insight**: Description of a pattern that isn't immediately apparent
- **supporting_evidence**: What comments support this
- **opportunity**: Potential product/feature opportunity

## Cross-Thread Aggregation Rules

When combining findings across all analyzed threads:

1. **Merge duplicates** — same problem described differently across threads
2. **Rank by frequency AND severity** — 5 people at high severity > 20 at low severity
3. **Identify cross-thread patterns** — problems confirmed in 3+ threads are high confidence
4. **Flag single-thread insights** — may be niche or under-discussed
5. **Generate top 10 opportunities** ranked by actionability

### Per-Opportunity Output

| Field | Description |
|-------|-------------|
| rank | 1-10 |
| title | Concise name |
| description | 2-3 sentence explanation |
| evidence_strength | weak / moderate / strong (based on thread + comment count) |
| pain_level | 1-5 scale |
| existing_solutions | What people currently use |
| gap | What's missing |
| willingness_to_pay | Signals from the data |
| recommended_validation | Suggested next step to validate |

## Signal vs Noise Guide

### Strong Signals (weight heavily)
- "I'm currently using [Tool A] + [Tool B] + a spreadsheet"
- "I'd pay for something that just handled [specific thing]"
- "I know this is a weird setup, but it's the only way I could make it work"
- Money or time quantified: "I spend 3 hours a week on..."
- Workarounds involving 3+ tools stitched together

### Noise (filter out)
- "Someone should build..." (daydreaming, no intent)
- "Wouldn't it be cool if..." (no pain behind it)
- Feature requests without context about why current options fail
- Memes, jokes, off-topic arguments
- Single-word responses or low-effort comments
