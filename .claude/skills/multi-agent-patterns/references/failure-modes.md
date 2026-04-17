# Failure Modes and Mitigations

Common failure patterns in multi-agent systems with concrete mitigations. Load when debugging or designing resilience.

---

## Failure 1: Supervisor Bottleneck

**What happens:** Supervisor accumulates context from all workers. After ~5 worker interactions, supervisor context saturates and performance degrades.

**Signals:** Supervisor starts repeating worker outputs, loses earlier decisions, makes inconsistent routing choices.

**Mitigation:**
1. Implement output schema constraints (workers return structured summaries, not raw text)
2. Use checkpointing to persist supervisor state without carrying full history
3. For high worker counts (5+), switch to swarm or hierarchical pattern

```python
# Structured output prevents context bloat
class WorkerOutput(BaseModel):
    finding: str           # Summary only — not full context
    evidence: list[str]    # file:line or URL references
    action_needed: bool    # Does supervisor need to route elsewhere?

# Supervisor reads structured fields, not raw worker conversation
```

---

## Failure 2: Coordination Overhead

**What happens:** Agent communication consumes so many tokens and adds so much latency that it negates parallelization benefits.

**Signals:** Multi-agent run takes longer than sequential single-agent equivalent; token cost exceeds expected 15× multiplier.

**Mitigation:**
1. Minimize communication through clear upfront handoff protocols
2. Batch results where possible (don't return after each subtask if subtasks can combine)
3. Use asynchronous communication patterns where ordering allows
4. If overhead still exceeds benefit → revert to single agent + model upgrade

---

## Failure 3: Divergence

**What happens:** Agents pursue different interpretations of the goal without central coordination. Outputs are internally inconsistent.

**Signals:** Agent A's output contradicts Agent B's output; final synthesis is incoherent.

**Mitigation:**
1. Define explicit objective boundaries for each agent in the dispatch prompt
2. Implement convergence checks every N iterations (compare agent outputs for consistency)
3. Use time-to-live limits on agent execution (prevents agents stuck in local optima)
4. For swarm patterns: designate a "convergence agent" that periodically checks alignment

---

## Failure 4: Error Propagation

**What happens:** Agent A's incorrect output is consumed by Agent B as truth, compounding the error.

**Signals:** Final output contains a claim that was wrong in an intermediate agent's output; the error appears in multiple agents' outputs.

**Mitigation:**
1. Validate agent outputs before passing to downstream agents
2. Implement retry logic with circuit breakers for deterministic tasks
3. Use idempotent operations where possible
4. Cross-validate critical findings with a second independent agent

```python
def validate_agent_output(output: WorkerOutput, schema: type) -> bool:
    """
    Validate output structure AND basic content sanity before passing downstream.
    Return False if validation fails — do NOT pass invalid output.
    """
    try:
        parsed = schema.model_validate(output)
        return len(parsed.finding) > 0 and parsed.confidence > 0.0
    except ValidationError:
        return False
```

---

## Failure 5: Sycophancy / False Consensus

**What happens:** Agents in a group setting converge on each other's answers through social pressure (mimicry), not independent reasoning. The consensus is wrong.

**Signals:** All agents suddenly agree after one agent makes a confident-sounding claim; no agent presents new evidence.

**Detection:**
```python
def detect_sycophancy_markers(messages: list[str]) -> bool:
    sycophancy_phrases = [
        "you're right", "I agree", "that's correct", "good point",
        "as you mentioned", "building on what"
    ]
    # If >60% of recent messages contain agreement markers with no new evidence → sycophancy
    ...
```

**Mitigation:**
1. Weighted voting: weight by confidence AND evidence quality, not just confidence
2. Debate protocol: require agents to critique each other before consensus
3. Independent sampling: request outputs separately before any agent sees others' outputs
4. Adversarial trigger: if sycophancy detected, inject a "contrarian" agent prompt

---

## Failure 6: Team Shutdown Neglect (Claude Code Specific)

**What happens:** Agent teams created via `TeamCreate` are never shut down. Idle teammates accumulate, consuming resources.

**Signals:** `TaskList` shows teams in "idle" state long after work completed; costs increase without corresponding output.

**Mitigation (mandatory for every TeamCreate session):**
```python
# ALWAYS at end of Agent Team session:
for teammate in team.members:
    SendMessage(team_id=team.id, to=teammate, message="shutdown_request")
TeamDelete(team_id=team.id)
```

**See:** `subagent-driven-development` skill for full team lifecycle management.

---

## Failure Summary Table

| Failure | Pattern affected | Severity | Primary mitigation |
|---------|-----------------|----------|--------------------|
| Supervisor bottleneck | Supervisor | HIGH | Structured output schemas + checkpointing |
| Coordination overhead | All | MEDIUM | Batch results, async comms |
| Divergence | Swarm | HIGH | Convergence checks + TTL limits |
| Error propagation | All | HIGH | Output validation before passing downstream |
| Sycophancy | All | MEDIUM | Debate protocol + independent sampling |
| Team shutdown neglect | Claude Code | MEDIUM | Always send shutdown_request + TeamDelete |
