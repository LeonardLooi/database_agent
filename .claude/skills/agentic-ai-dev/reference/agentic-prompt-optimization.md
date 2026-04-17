# Agentic AI Prompt Optimization

Advanced prompt optimization techniques for production LangGraph/LangChain agents. Extends `agentic-prompt-engineering.md` with techniques for constitutional AI, tree-of-thoughts, multi-model templates, and production prompt lifecycle management.

---

## 1. Constitutional AI Self-Critique Loop

A 3-pass generate → critique → refine pattern. Use inside a LangGraph node when output quality must be validated before returning to the user.

```python
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class ConstitutionalState(TypedDict):
    input: str
    draft_response: str
    critique: str
    final_response: str
    iteration_count: int  # REQUIRED — prevents runaway loops

CRITIQUE_SYSTEM = """Review the response against these principles:
1. ACCURACY: Are all claims verifiable? Flag uncertainties with "I'm not certain that..."
2. SAFETY: Does it contain harm, bias, or ethical concerns?
3. QUALITY: Is it clear, consistent, and complete?

Output format:
- PASS: [brief reason] — if response meets all 3 criteria
- REVISE: [specific issue and correction needed] — if any criterion fails"""

REFINE_SYSTEM = """You are revising a response based on critique feedback.
Apply the critique exactly. Do not introduce new content beyond what the critique requires."""

async def constitutional_node(state: ConstitutionalState) -> ConstitutionalState:
    """3-pass self-critique node. Insert in graph before final response output."""
    llm = get_llm()  # from agentic-llm-routing.md factory

    # Pass 1: Generate draft
    draft = await llm.ainvoke([HumanMessage(content=state["input"])])
    draft_text = draft.content

    # Pass 2: Critique
    critique = await llm.ainvoke([
        SystemMessage(content=CRITIQUE_SYSTEM),
        HumanMessage(content=f"Response to review:\n{draft_text}")
    ])

    # Pass 3: Refine only if critique found issues
    if critique.content.startswith("PASS"):
        final = draft_text
    else:
        refined = await llm.ainvoke([
            SystemMessage(content=REFINE_SYSTEM),
            HumanMessage(content=f"Original: {draft_text}\n\nCritique: {critique.content}\n\nRevised response:")
        ])
        final = refined.content

    return {
        **state,
        "draft_response": draft_text,
        "critique": critique.content,
        "final_response": final,
    }
```

**When to use:** Customer-facing responses, medical/legal/financial content, any output where hallucinations have high cost.

**Cost:** 2–3× LLM calls per request. Use for high-stakes paths only — not on every node.

---

## 2. Tree-of-Thoughts (ToT)

Multi-path exploration with scoring. Use when a single reasoning path produces poor results (complex analysis, multi-step planning).

```python
TOT_TEMPLATE = """Explore multiple solution paths for this problem.

Problem: {problem}

**Approach A:** [Describe path 1 — most straightforward]
- Feasibility: [1-10]
- Completeness: [1-10]
- Efficiency: [1-10]
- Verdict: [proceed / abandon]

**Approach B:** [Describe path 2 — alternative angle]
- Feasibility: [1-10]
- Completeness: [1-10]
- Efficiency: [1-10]
- Verdict: [proceed / abandon]

**Approach C:** [Describe path 3 — unconventional]
- Feasibility: [1-10]
- Completeness: [1-10]
- Efficiency: [1-10]
- Verdict: [proceed / abandon]

**Selected Approach:** [A / B / C — highest combined score]
**Rationale:** [Why this path wins]

**Implementation:**
[Execute the selected approach fully]"""

async def tot_node(state: AgentState) -> AgentState:
    """Tree-of-thoughts reasoning node."""
    llm = get_llm()
    response = await llm.ainvoke([
        HumanMessage(content=TOT_TEMPLATE.format(problem=state["messages"][-1].content))
    ])
    return {**state, "messages": state["messages"] + [response]}
```

**When to use:** Architecture decisions, multi-step planning, code refactoring strategies, research synthesis.

**When NOT to use:** Simple lookups, direct factual questions, tasks with a single obvious correct approach.

---

## 3. Model-Specific Prompt Templates

Different models respond better to different prompt structures. Use these when the agent's `llm` provider differs.

### Claude 4.5 / Claude 4 (Anthropic)

Claude responds best to XML-structured prompts with explicit thinking blocks:

```python
CLAUDE_TEMPLATE = """<context>
{background_information}
</context>

<task>
{clear_objective}
</task>

<constraints>
{explicit_limitations}
</constraints>

<thinking>
Work through this step by step before answering.
</thinking>

<output_format>
{specify_expected_structure}
</output_format>"""

# In LangGraph — use as system message
claude_system = SystemMessage(content=CLAUDE_TEMPLATE.format(
    background_information=context,
    clear_objective=task,
    explicit_limitations=constraints,
    specify_expected_structure=output_spec,
))
```

### Gemini Pro / Ultra (Google)

Gemini responds best to Markdown-structured prompts with explicit process steps and quality constraints. **See `google-adk/reference/adk-gemini-prompt-templates.md` for full ADK-specific Gemini patterns.**

```python
GEMINI_TEMPLATE = """**System Context:** {background}
**Primary Objective:** {goal}

**Process:**
1. {action_step_1}
2. {action_step_2}
3. Verify output against quality constraints below

**Output Structure:**
- Format: {output_type}
- Length: {target_length}
- Style: {tone}

**Quality Constraints:**
- Factual accuracy with inline citations where applicable
- No speculation without explicit "I believe..." qualifier
- Flag gaps: state explicitly what information is missing"""
```

### GPT-4o / GPT-5 (OpenAI)

GPT responds best to section-delimited prompts with explicit JSON output format:

```python
GPT_TEMPLATE = """##CONTEXT##
{structured_context}

##OBJECTIVE##
{specific_goal}

##INSTRUCTIONS##
1. {numbered_step_1}
2. {numbered_step_2}
3. {numbered_step_3}

##OUTPUT FORMAT##
```json
{
  "result": "...",
  "reasoning": "...",
  "confidence": 0.0
}
```

##EXAMPLES##
{few_shot_examples}"""
```

**How to select at runtime:**

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

def get_prompt_template(provider: str) -> str:
    """Return model-appropriate prompt template."""
    return {
        "anthropic": CLAUDE_TEMPLATE,
        "google": GEMINI_TEMPLATE,
        "openai": GPT_TEMPLATE,
    }.get(provider, CLAUDE_TEMPLATE)  # default to Claude

# In agentic-llm-routing.md — the factory already knows the provider
```

---

## 4. Prompt Versioning Registry

Track prompt versions in production. Enables A/B testing and safe rollback.

```python
from dataclasses import dataclass, field
from typing import Optional
import hashlib

@dataclass
class PromptVersion:
    version: str                    # semver: "1.0.0"
    prompt_template: str            # the actual prompt
    model: str                      # "claude-sonnet-4-5", "gemini-3.1-flash-exp"
    description: str                # what changed from previous version
    traffic_percent: float = 100.0  # percentage of traffic this version handles
    performance_baseline: Optional[float] = None  # success rate from evaluation

    @property
    def checksum(self) -> str:
        """Detect accidental prompt mutation."""
        return hashlib.sha256(self.prompt_template.encode()).hexdigest()[:8]

class PromptRegistry:
    """Production prompt version manager.

    Usage:
        registry = PromptRegistry()
        registry.register("rag-synthesis", PromptVersion("1.0.0", template_v1, ...))
        registry.register("rag-synthesis", PromptVersion("1.1.0", template_v2, ..., traffic_percent=5.0))

        prompt = registry.get("rag-synthesis", user_id="u123")
    """
    def __init__(self):
        self._versions: dict[str, list[PromptVersion]] = {}

    def register(self, name: str, version: PromptVersion) -> None:
        self._versions.setdefault(name, []).append(version)

    def get(self, name: str, user_id: str = "") -> PromptVersion:
        """Route traffic by version weights. Deterministic per user_id."""
        versions = self._versions.get(name, [])
        if not versions:
            raise KeyError(f"No prompt registered: {name}")
        if len(versions) == 1:
            return versions[-1]
        # Canary routing: hash user_id for consistent assignment
        bucket = int(hashlib.md5(user_id.encode()).hexdigest(), 16) % 100
        cumulative = 0.0
        for v in reversed(versions):  # newest first
            cumulative += v.traffic_percent
            if bucket < cumulative:
                return v
        return versions[0]  # fallback to first version
```

---

## 5. Canary Rollout Strategy

Deploy prompt changes progressively. Never flip 100% at once.

```python
ROLLOUT_STAGES = [5, 10, 25, 50, 100]  # percent of traffic per stage
ROLLBACK_THRESHOLD = 0.10              # rollback if error rate > 10%
STAGE_DURATION = "24h"                 # minimum time at each stage before promoting

# Stage 1: Register new version at 5% traffic
registry.register("my-prompt", PromptVersion(
    version="1.1.0",
    prompt_template=new_template,
    model="claude-sonnet-4-5",
    description="Added constitutional AI self-critique step",
    traffic_percent=5.0,
))

# Monitor: check error rate from observability (agentic-observability.md)
# If error_rate > ROLLBACK_THRESHOLD: set traffic_percent back to 0.0
# If healthy after STAGE_DURATION: promote to next stage (10%, 25%, 50%, 100%)

# Stage gate check (run from CI or cron):
def should_promote(name: str, current_stage: int, error_rate: float) -> bool:
    if error_rate > ROLLBACK_THRESHOLD:
        logger.warning("prompt_rollback", name=name, error_rate=error_rate)
        return False
    next_stage_idx = ROLLOUT_STAGES.index(current_stage) + 1
    if next_stage_idx >= len(ROLLOUT_STAGES):
        return False  # already at 100%
    return True
```

**Rollback procedure:**

```python
def rollback(name: str, to_version: str) -> None:
    """Immediate rollback: set traffic to 100% for stable version."""
    for v in registry._versions[name]:
        v.traffic_percent = 100.0 if v.version == to_version else 0.0
    logger.warning("prompt_emergency_rollback", name=name, to_version=to_version)
```

---

## 6. LLM-as-Judge Evaluation

Evaluate prompt output quality programmatically. Use in CI and canary validation.

```python
JUDGE_PROMPT = """Evaluate the quality of this AI response.

## Original Task
{task}

## AI Response
{response}

## Rate each dimension 1–10 with one-sentence justification:
1. TASK_COMPLETION: Did the response fully address the task?
2. ACCURACY: Is the response factually correct and well-reasoned?
3. FORMAT: Does the output match the required format?
4. SAFETY: Is the response free of bias, harmful content, or hallucinations?

## Overall Score: [sum]/40
## Recommendation: Accept | Revise | Reject"""

async def evaluate_with_judge(
    task: str,
    response: str,
    judge_llm = None,
) -> dict:
    """Run LLM-as-judge evaluation. Returns structured scores."""
    judge = judge_llm or get_llm()  # use separate judge model in production
    result = await judge.ainvoke([
        HumanMessage(content=JUDGE_PROMPT.format(task=task, response=response))
    ])
    # Parse scores — in production, use .with_structured_output(JudgeResult)
    return {"raw": result.content, "response_evaluated": response[:100]}

# Integration with LangSmith (from agentic-observability.md):
# from langsmith import evaluate
# results = evaluate(evaluate_with_judge, data=dataset_name, ...)
```

---

## When to Load This File

Load `agentic-prompt-optimization.md` when:
- Output quality is insufficient and a single prompt pass isn't enough
- Building customer-facing agents where hallucinations have high cost (constitutional AI)
- Choosing prompt structure for a non-Claude model (model-specific templates)
- Preparing to change a prompt in production (versioning + canary rollout)
- Setting up automated quality gates for agent output (LLM-as-judge)

For baseline prompting (CoT, structured output, system prompt templates, injection defense, context engineering), use `agentic-prompt-engineering.md` instead.
