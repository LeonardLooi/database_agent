# ADK Gemini Prompt Templates

Gemini-specific prompt engineering patterns for Google ADK `LlmAgent` instructions. Gemini responds best to Markdown-structured prompts with explicit process steps, clear output constraints, and inline citation guidance.

Use these templates in the `instruction` field of `LlmAgent(instruction=...)` or in `before_model_callback` for dynamic injection.

---

## 1. Base Gemini Template Structure

Gemini processes Markdown headers and bold text as structural cues. Use this base structure for any `LlmAgent` instruction:

```python
GEMINI_BASE_INSTRUCTION = """**System Context:** {background}
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
- Factual accuracy: cite sources inline as [Source: reference] where applicable
- No speculation without explicit qualifier: "Based on available information..."
- Flag information gaps: state explicitly what is unknown or uncertain"""

# Usage in ADK:
from google.adk.agents import LlmAgent

research_agent = LlmAgent(
    name="research_agent",
    model="gemini-3.1-flash-exp",
    instruction=GEMINI_BASE_INSTRUCTION.format(
        background="You are a research assistant for a software engineering team.",
        goal="Answer technical questions with accurate, cited information.",
        action_step_1="Identify the core question and required knowledge domains",
        action_step_2="Use available tools to retrieve current, accurate information",
        output_type="Markdown with headers",
        target_length="200-400 words unless detail is required",
        tone="Technical but accessible",
    ),
)
```

---

## 2. RAG Agent Instruction (Gemini)

For agents using retrieval tools (`load_memory`, custom search tools):

```python
GEMINI_RAG_INSTRUCTION = """**Role:** Document analysis specialist with access to a knowledge base.

**On every query:**
1. RETRIEVE: Use available search tools to find relevant documents
2. ASSESS RELEVANCE: For each retrieved document, note confidence (high/medium/low)
3. SYNTHESIZE: Combine information from multiple sources; cite as [Doc: title or ID]
4. IDENTIFY GAPS: If retrieved documents don't fully answer the query, state this explicitly
5. RESPOND: Comprehensive answer with inline citations

**Citation format:** "According to [Doc: {source_name}], {finding}."

**When information is missing:**
"The available documents do not contain information about {topic}.
The following aspects remain uncertain: {list_gaps}."

**Quality gate before responding:**
- Am I citing sources for factual claims? [verify]
- Have I stated confidence levels? [verify]
- Have I flagged gaps? [verify]"""

rag_agent = LlmAgent(
    name="rag_agent",
    model="gemini-3.1-flash-exp",
    instruction=GEMINI_RAG_INSTRUCTION,
    tools=[load_memory_tool, search_documents_tool],
)
```

---

## 3. Constitutional AI for ADK Agents

Implement self-critique using a two-agent ADK pattern: a generator agent and a critique agent in sequence.

```python
from google.adk.agents import LlmAgent, SequentialAgent

GENERATOR_INSTRUCTION = """Generate a response to the user's request.
Be thorough and accurate. Use available tools if needed.
Store your response in session state as output_key="draft_response"."""

CRITIC_INSTRUCTION = """You are a quality reviewer. Review the draft_response in session state.

**Evaluate against:**
1. ACCURACY: Are all claims verifiable? Are there unsupported assertions?
2. SAFETY: Any harmful, biased, or misleading content?
3. COMPLETENESS: Are important aspects missing?

**If PASS:** Output the draft_response unchanged with "QUALITY: PASS" prefix.
**If REVISE:** Output an improved version with "QUALITY: REVISED — [reason]" prefix.

Access draft: use get_session_state tool to read "draft_response"."""

generator = LlmAgent(
    name="generator",
    model="gemini-3.1-flash-exp",
    instruction=GENERATOR_INSTRUCTION,
    output_key="draft_response",
)

critic = LlmAgent(
    name="critic",
    model="gemini-3.1-flash-exp",
    instruction=CRITIC_INSTRUCTION,
    output_key="final_response",
)

constitutional_agent = SequentialAgent(
    name="constitutional_pipeline",
    sub_agents=[generator, critic],
)
```

**Cost:** 2× model calls per request. Use for high-stakes outputs (user-facing responses, medical/legal/financial content).

---

## 4. Tree-of-Thoughts for ADK

Use inside a `LoopAgent` where the agent explores multiple approaches before committing:

```python
TOT_INSTRUCTION = """Solve the given problem by exploring multiple approaches.

**Step 1 — Generate 3 approaches:**
Approach A: [Most direct path]
Approach B: [Alternative angle]
Approach C: [Creative/unconventional]

**Step 2 — Score each (1-10):**
- Feasibility: Can this be done with available tools and information?
- Completeness: Does it fully address the problem?
- Efficiency: Is it appropriately concise?

**Step 3 — Select and implement:**
Selected: [A/B/C — highest total score]
Rationale: [One sentence why]

**Implementation:**
[Execute the selected approach in full]

Call exit_loop when implementation is complete."""

tot_agent = LlmAgent(
    name="tot_reasoner",
    model="gemini-3.1-flash-exp",  # Flash is sufficient for scoring; use Pro for complex domains
    instruction=TOT_INSTRUCTION,
    tools=[exit_loop],
)
```

---

## 5. Multi-Step Analysis Agent

For agents that perform structured analysis (data analysis, document review, architecture evaluation):

```python
GEMINI_ANALYSIS_INSTRUCTION = """**Role:** Senior analyst with domain expertise.

**Analysis Framework (apply in order):**

### Phase 1: Scope
- Core question or objective
- Data/information available
- Constraints and assumptions

### Phase 2: Investigation
- Use tools to gather relevant data
- Identify patterns, anomalies, or key findings
- Note statistical significance where applicable

### Phase 3: Synthesis
- Top 3 findings (ranked by impact)
- Supporting evidence for each
- Confidence level: high (verified) / medium (inferred) / low (speculative)

### Phase 4: Recommendations
- Immediate actions (quick wins)
- Strategic actions (longer term)
- Risks to monitor

**Output format:**
```yaml
findings:
  - insight: [finding]
    evidence: [data point or source]
    confidence: high|medium|low
    action: [recommended next step]
recommendations:
  immediate: []
  strategic: []
  risks: []
```
"""
```

---

## 6. Prompt Optimization Patterns Specific to Gemini

**What works well with Gemini:**
- Markdown `**bold**` and `###` headers for structure (processed as semantic cues)
- Explicit numbered process steps (Gemini follows ordered instructions reliably)
- Inline citation requests ("cite as [Source: X]")
- `output_schema` with Pydantic for structured output — prefer over asking for JSON in instruction
- Temperature 0.1–0.3 for factual tasks; 0.7–0.9 for creative tasks

**What to avoid with Gemini:**
- XML tags (`<context>`, `<task>`) — these are Claude-optimized patterns, less effective with Gemini
- Very long monolithic instruction blocks — break into phases with headers instead
- Asking for JSON in instruction text — use `output_schema=PydanticModel` instead (see `adk-structured-output.md`)
- `##SECTION##` delimiters — GPT-optimized, not Gemini-optimized

**Model selection within Gemini family:**

| Task | Recommended Model | Reason |
|------|------------------|--------|
| Standard agent tasks | `gemini-3.1-flash-exp` | Fast, cost-effective, strong instruction following |
| Complex reasoning (ToT, multi-step analysis) | `gemini-2.0-pro-exp` | Better at multi-step reasoning chains |
| Long document RAG (>100k tokens) | `gemini-3.1-flash-exp` | 1M token context window |
| Code generation | `gemini-3.1-flash-exp` | Strong coding, fast iteration |

---

## When to Load This File

Load when:
- Writing `instruction` strings for ADK `LlmAgent` with `model="gemini-*"`
- Setting up multi-agent constitutional AI pipelines in ADK (`SequentialAgent` with critic)
- Building RAG agents in ADK with citation requirements
- Comparing prompt structure across models (see `agentic-prompt-optimization.md` for LangGraph equivalents)
- Choosing between `gemini-3.1-flash-exp` and `gemini-2.0-pro-exp` for a task

**Related:** `agentic-prompt-optimization.md` in `agentic-ai-dev/reference/` — same techniques expressed as LangGraph nodes.
