# Architectural Patterns

Deep reference for the three multi-agent architectural patterns. Load when choosing a pattern or implementing a new system.

---

## Pattern 1: Supervisor / Orchestrator

**Structure:**
```
User Query → Supervisor → [Specialist A, Specialist B, Specialist C] → Aggregation → Final Output
```

**When to use:**
- Complex tasks with clear decomposition
- Tasks requiring coordination across domains
- Human oversight and intervention points are important
- You need predictable, auditable execution flow

**Advantages:**
- Strict workflow control
- Easy to implement human-in-the-loop interventions
- Ensures adherence to predefined plans
- Easier to debug (central state, single decision point)

**Disadvantages:**
- Supervisor context becomes a bottleneck as workers multiply
- Supervisor failures cascade to all workers
- Telephone game problem (see SKILL.md — mitigate with `forward_message`)

**Implementation template (LangGraph):**
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class SupervisorState(TypedDict):
    messages: Annotated[list, operator.add]
    next_worker: str
    task_complete: bool

def supervisor_node(state: SupervisorState) -> SupervisorState:
    """Central coordinator — routes to specialists, tracks progress."""
    # Analyze current state, decide which worker to route to
    # Only synthesize when aggregation is genuinely needed
    # Use forward_message for final/complete worker outputs
    ...

def specialist_node(state: SupervisorState) -> SupervisorState:
    """Domain specialist — executes single task in clean context."""
    ...

graph = StateGraph(SupervisorState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("researcher", specialist_node)
graph.add_node("analyzer", specialist_node)
graph.add_conditional_edges(
    "supervisor",
    lambda state: state["next_worker"],
    {"researcher": "researcher", "analyzer": "analyzer", "END": END}
)
```

**Checkpointing (prevents supervisor context saturation):**
```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

# Supervisor writes distilled summaries, not full worker outputs
# Workers return structured output schemas, not raw text
```

---

## Pattern 2: Peer-to-Peer / Swarm

**Structure:**
```
Any agent can transfer control to any other via explicit handoff
```

```python
def transfer_to_agent_b():
    return agent_b  # Handoff via function return

agent_a = Agent(
    name="Agent A",
    functions=[transfer_to_agent_b]
)
```

**When to use:**
- Tasks requiring flexible exploration where rigid upfront planning is counterproductive
- Tasks with emergent requirements that defy decomposition
- Breadth-first search patterns (research, discovery)
- When speed matters more than predictability

**Advantages:**
- No single point of failure (supervisor failure doesn't cascade)
- Scales for breadth-first exploration
- Enables emergent problem-solving
- Sub-agents respond directly to users (eliminates telephone game)

**Disadvantages:**
- Coordination complexity grows with agent count
- Risk of divergence without central state keeper
- Requires robust convergence constraints to prevent infinite loops

**Convergence constraints (mandatory):**
```python
class SwarmConfig:
    max_iterations: int = 10        # Hard loop limit
    max_agent_hops: int = 5         # Prevent infinite handoff chains
    time_to_live_seconds: int = 300 # Wall-clock termination
    convergence_check_interval: int = 3  # Check every N iterations
```

**Sycophancy prevention:**
```python
def detect_sycophancy(agent_outputs: list[str]) -> bool:
    """
    Returns True if agents are converging on each other's answers
    without independent reasoning — signals sycophancy, not consensus.
    """
    # Check semantic similarity between outputs
    # If agents are mirroring without new evidence, trigger debate protocol
    ...
```

---

## Pattern 3: Hierarchical

**Structure:**
```
Strategy Layer (Goal Definition)
    ↓
Planning Layer (Task Decomposition)
    ↓
Execution Layer (Atomic Tasks)
```

**When to use:**
- Large-scale projects with clear hierarchical structure
- Enterprise workflows with management layers
- Tasks requiring both high-level planning and detailed execution
- When strategy must be isolated from implementation concerns

**Advantages:**
- Mirrors organizational structures (familiar to teams)
- Clear separation of concerns
- Different context structures optimized per layer
- Strategy layer can be human-controlled

**Disadvantages:**
- Coordination overhead between layers
- Potential for misalignment (strategy sets goal, execution finds it's infeasible)
- Complex error propagation (execution failure must bubble up through planning to strategy)

**Error propagation in hierarchical systems:**
```
Execution failure
    → Planning layer: Is this task replaceable? Can a workaround be found?
        YES → Replanning. Notify execution layer with revised tasks.
        NO → Escalate to Strategy layer with: failed task + impact + options.
            → Strategy layer: Adjust goal scope OR accept failure OR escalate to human.
```

**Alignment check (run periodically):**
```python
def alignment_check(
    strategy_goal: str,
    planning_tasks: list[str],
    execution_outputs: list[str]
) -> dict:
    """
    Verify execution outputs trace back to planning tasks,
    and planning tasks trace back to strategy goal.
    Return gaps where execution drifted from intent.
    """
    ...
```

---

## Pattern Comparison for This Workspace

| Use Case | Recommended Pattern |
|----------|-------------------|
| NestJS feature with backend + frontend + DB | Supervisor (clear decomposition, 3 specialists) |
| LangGraph research agent exploring multiple sources | Swarm (emergent, parallel exploration) |
| Flutter feature with UI + state + Firebase | Supervisor (3 specialists in sequence) |
| Enterprise ADK agent (goal setting → plan → execute) | Hierarchical |
| Full security audit (config + code + pentest) | Supervisor with 3 specialized reviewer agents |
| Autonomous PR iteration loop | Swarm (retry until convergence) |
