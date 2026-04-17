---
name: prompt-engineering-patterns
description: "Advanced prompt engineering for production LLM applications with LangGraph and Google ADK. Covers few-shot learning, chain-of-thought, Tree-of-Thought, self-consistency, system prompt design, prompt optimization, and reusable templates. Use when designing agent system prompts, implementing structured reasoning, optimizing LLM outputs, or debugging inconsistent model responses."
allowed-tools: Bash, Read, Write, Edit
metadata:
  triggers: prompt engineering, few-shot, chain of thought, tree of thought, self-consistency, system prompt design, prompt optimization, prompt template, CoT, ToT, LLM prompting, agent instruction, structured reasoning, prompt debugging, prompt versioning
  related-skills: agentic-ai-dev, google-adk, agentic-ai-coding-standard, gemini-api-dev
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-15"
---

## Iron Law

**NO SYSTEM PROMPT WITHOUT ROLE + TASK + OUTPUT FORMAT — vague system prompts produce inconsistent LLM outputs and degrade agent reliability in both LangGraph and ADK. Every agent instruction must state what the agent IS, what it DOES, and what format it RETURNS.**

# Prompt Engineering Patterns — LangGraph + Google ADK

## When to Use This Skill

- Designing or reviewing system prompts / ADK agent instructions
- LLM outputs are inconsistent or hallucinating — apply CoT or self-consistency
- Output format needs demonstration — apply few-shot learning
- Complex multi-step reasoning required — apply chain-of-thought
- Need to explore multiple solution paths — apply Tree-of-Thought
- Reducing prompt token cost while keeping quality — prompt optimization
- Building reusable, testable prompt templates

## Framework Decision Tree

```
What's the problem?
├── Output format is wrong / inconsistent
│   └── Apply Few-Shot Learning → reference/few-shot-learning.md
├── Model skips reasoning steps / wrong answers on complex tasks
│   └── Apply Chain-of-Thought → reference/chain-of-thought.md
├── Need to explore multiple solution branches
│   └── Apply Tree-of-Thought → reference/chain-of-thought.md#tot
├── Need highest accuracy (can afford 3-5x cost)
│   └── Apply Self-Consistency → reference/chain-of-thought.md#self-consistency
├── System prompt is vague or producing variable behavior
│   └── Apply System Prompt Design → reference/system-prompts.md
├── Prompts are too long / expensive / slow
│   └── Apply Prompt Optimization → reference/prompt-optimization.md
└── Need reusable structured prompts across agents
    └── Apply Template Patterns → reference/prompt-templates.md
```

## Key Patterns

| Pattern | When | LangGraph | Google ADK | Reference |
|---------|------|-----------|------------|-----------|
| Few-Shot | Output format needs demonstration | `HumanMessage` with examples in node prompt | `instruction=` block with examples | `reference/few-shot-learning.md` |
| Chain-of-Thought | Multi-step reasoning, math, debugging | `SystemMessage` with "think step by step" | `instruction=` with numbered steps | `reference/chain-of-thought.md` |
| Tree-of-Thought | Complex exploration / planning | Parallel branch nodes + aggregator | `ParallelAgent` + synthesizer | `reference/chain-of-thought.md` |
| Self-Consistency | High-accuracy critical tasks | Multiple `llm.invoke()` + majority vote | Multiple ADK runs + vote | `reference/chain-of-thought.md` |
| System Prompt Design | Define agent role, behavior, constraints | `SystemMessage` as first message | `LlmAgent(instruction=...)` | `reference/system-prompts.md` |
| Prompt Templates | Reusable structured prompts | f-string + `SystemMessage` | `instruction=` with `{variable}` | `reference/prompt-templates.md` |
| Prompt Optimization | Reduce tokens, improve consistency | Offline A/B test framework | Offline A/B test framework | `reference/prompt-optimization.md` |

## Instruction Hierarchy (Universal Rule)

Always structure prompts in this order:

```
[System Context / Role]     <- who the agent IS
[Task Instruction]          <- what it MUST DO
[Constraints]               <- what it MUST NOT DO
[Examples / Few-Shot]       <- show, don't just tell
[Input Data]                <- the actual input
[Output Format]             <- exact expected output shape
```

## Quick Examples

### LangGraph — CoT Node
```python
from langchain_core.messages import SystemMessage, HumanMessage

COT_SYSTEM = SystemMessage(content="""You are a senior software architect.
When analyzing a problem:
1. State your understanding of the problem
2. Identify constraints and requirements
3. Consider 2-3 solution approaches with trade-offs
4. Select the best approach with justification
5. Outline implementation steps

Always show your reasoning explicitly before giving a recommendation.""")

def analysis_node(state: AgentState) -> AgentState:
    response = llm.invoke([COT_SYSTEM, HumanMessage(content=state["problem"])])
    return {"analysis": response.content}
```

### Google ADK — CoT Agent
```python
from google.adk.agents import LlmAgent

analysis_agent = LlmAgent(
    name="analysis_agent",
    model="gemini-3.1-flash",
    instruction="""You are a senior software architect.
When analyzing a problem, follow these steps explicitly:
1. State your understanding of the problem
2. Identify constraints and requirements
3. Consider 2-3 solution approaches with trade-offs
4. Select the best approach with justification
5. Outline implementation steps

Always show your reasoning before giving a recommendation.
Output format: structured analysis with sections for Understanding, Options, Decision, and Next Steps."""
)
```

## Reference Files

| File | Content | When to Load |
|------|---------|--------------|
| `reference/chain-of-thought.md` | CoT, ToT, Self-Consistency patterns with LangGraph + ADK code | Complex reasoning, multi-step tasks |
| `reference/few-shot-learning.md` | Example selection, dynamic retrieval, edge cases — LangGraph + ADK | Inconsistent output format, classification tasks |
| `reference/prompt-optimization.md` | A/B testing, token reduction, versioning, metrics | Reducing cost, improving consistency |
| `reference/system-prompts.md` | Role definition, constraints, output format — LangGraph + ADK | Designing new agent system prompts |
| `reference/prompt-templates.md` | Reusable templates, variable interpolation, multi-turn — LangGraph + ADK | Building template systems |
| `reference/prompt-template-library.md` | 15+ battle-tested copy-paste templates for common tasks | Finding a starting template fast |

## Post-Code Review

After writing prompts or agent instructions, verify:
- `agentic-ai-reviewer` — graph correctness, system prompt quality in LangGraph agents
- `security-reviewer` — prompt injection defense, no sensitive data in prompts
