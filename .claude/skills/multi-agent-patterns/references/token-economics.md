# Token Economics

Cost and performance data for multi-agent architecture decisions. Load before committing to a multi-agent approach.

---

## Token Multipliers (Production Data)

| Architecture | Token Multiplier | Typical Use Case |
|--------------|------------------|------------------|
| Single agent chat | 1× baseline | Simple queries, single-domain tasks |
| Single agent with tools | ~4× baseline | Tool-using tasks (file reads, API calls) |
| Multi-agent system | ~15× baseline | Complex research, cross-domain coordination |

**Implication:** A task that costs 10K tokens as a single agent costs ~150K tokens in a multi-agent system. Budget accordingly.

---

## Model vs. Parallelization

**Key finding from BrowseComp evaluation:** Three factors explain 95% of performance variance:
1. **Token usage** (80% of variance) — more tokens = better results
2. **Number of tool calls**
3. **Model choice**

**Critical insight:** Upgrading the model often outperforms doubling token budget.

| Upgrade | Typical improvement |
|---------|-------------------|
| Sonnet → Opus | Larger gain than doubling token budget |
| Single agent → 2 parallel sonnet agents | ~1.3–1.5× performance (diminishing returns) |
| Single Opus agent vs. 3 parallel sonnet | Often comparable, at lower token cost |

**Decision framework:**
```
Task failing with current model?
    ↓
Option A: Upgrade model (Sonnet → Opus) — likely 20–40% improvement
Option B: Add parallel agents — likely 15–30% improvement at 2–3× token cost

If Option A ≤ Option B in improvement AND cheaper in tokens → choose Option A first
If the task fundamentally requires parallelism (independent subtasks) → Option B
If budget allows both → combine: Opus supervisor + Sonnet specialists
```

---

## Context Window Degradation Thresholds

Even with 1M token context windows, degradation begins well before the limit.

| Threshold | Action |
|-----------|--------|
| 70–80% of window | Begin active compression |
| Lost-in-middle zone (center of context) | 10–40% lower recall — move critical info to start/end |
| Context poisoning | One hallucination reinforced every turn — restart context if outputs diverge |

**For multi-agent systems:**
- Sub-agents receive clean context = no degradation in early turns
- Supervisor accumulates all worker outputs = degrades fastest
- Mitigation: structured output schemas from workers (summaries, not raw text)

---

## Cost Estimation Template

Use before proposing multi-agent architecture:

```
Single-agent baseline:
- Estimated tokens per run: [N]
- Runs per day: [N]
- Daily cost: [N tokens × $X/1M tokens]

Multi-agent equivalent:
- Token multiplier: ~15×
- Estimated tokens per run: [N × 15]
- Daily cost: [N × 15 × $X/1M tokens]

Break-even analysis:
- Is the task currently failing with single agent? [YES/NO]
- Does the task have genuinely parallel subtasks? [YES/NO]
- Would model upgrade (Sonnet → Opus) solve the problem cheaper? [YES/NO]

Recommendation: [single agent | model upgrade | multi-agent | model upgrade + multi-agent]
```

---

## Token Budget by Pattern

| Pattern | Token Efficiency | Notes |
|---------|-----------------|-------|
| Supervisor with direct pass-through | High | Workers return to user directly — no synthesis cost |
| Supervisor with synthesis | Medium | Supervisor re-reads all worker outputs = linear context growth |
| Swarm | Medium-High | Independent contexts but handoff state must transfer |
| Hierarchical | Low-Medium | 3× planning overhead before any execution begins |

**Optimization:** Use output schema constraints so workers return distilled summaries, not full conversation history:

```python
class WorkerOutput(BaseModel):
    finding: str                    # 1-3 sentence summary
    evidence: list[str]             # file:line or URL references
    confidence: float               # 0.0-1.0
    requires_followup: bool         # Should supervisor route back to this worker?

# Workers return WorkerOutput, not raw text
# Supervisor reads structured fields, not full context
```
