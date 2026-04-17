# ADK Agent Types

## 1. SequentialAgent — Pipeline

Sub-agents execute in order. Each agent writes its output to `output_key` in session state. Downstream agents reference earlier outputs via `{key}` in their `instruction`.

```python
from google.adk import Agent, InMemoryRunner
from google.adk.agents import SequentialAgent
from google.genai import types


researcher = Agent(
    name="researcher",
    model="gemini-3.1-flash",
    description="Researches a topic and produces raw findings.",
    instruction=(
        "Research the topic provided by the user. "
        "Gather key facts, statistics, and relevant context. "
        "Write detailed findings as plain text."
    ),
    output_key="research_findings",
)

writer = Agent(
    name="writer",
    model="gemini-3.1-flash",
    description="Transforms research findings into a draft article.",
    instruction=(
        "You are a technical writer. Using the following research findings, "
        "write a clear, well-structured draft article:\n\n{research_findings}"
    ),
    output_key="draft_article",
)

editor = Agent(
    name="editor",
    model="gemini-3.1-flash",
    description="Edits and polishes a draft article.",
    instruction=(
        "You are a professional editor. Review and improve this draft article "
        "for clarity, grammar, and flow:\n\n{draft_article}\n\n"
        "Return only the final polished version."
    ),
    output_key="final_article",
)

pipeline = SequentialAgent(
    name="research_pipeline",
    description="Researches a topic, writes a draft, then edits it into a final article.",
    sub_agents=[researcher, writer, editor],
)

# Run the pipeline
runner = InMemoryRunner(agent=pipeline, app_name="pipeline_app")
session = runner.session_service.create_session(app_name="pipeline_app", user_id="u1")

for event in runner.run(
    user_id="u1",
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="Write an article about quantum computing.")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(part.text)

# Retrieve individual stage outputs from session state
final_session = runner.session_service.get_session(
    app_name="pipeline_app", user_id="u1", session_id=session.id
)
print(final_session.state.get("research_findings"))
print(final_session.state.get("draft_article"))
print(final_session.state.get("final_article"))
```

## 2. ParallelAgent — Concurrent Analysis

Sub-agents execute concurrently and independently. Each writes to its own `output_key`. A downstream synthesizer (in a SequentialAgent wrapper) reads all keys.

```python
from google.adk import Agent, InMemoryRunner
from google.adk.agents import ParallelAgent, SequentialAgent
from google.genai import types


technical_analyst = Agent(
    name="technical_analyst",
    model="gemini-3.1-flash",
    description="Analyzes the technical aspects of a topic.",
    instruction=(
        "Analyze the technical feasibility and implementation details of: {topic}. "
        "Focus on technology, infrastructure, and technical risks."
    ),
    output_key="technical_analysis",
)

market_analyst = Agent(
    name="market_analyst",
    model="gemini-3.1-flash",
    description="Analyzes the market opportunity and competitive landscape.",
    instruction=(
        "Analyze the market opportunity for: {topic}. "
        "Cover market size, competitors, and growth potential."
    ),
    output_key="market_analysis",
)

risk_analyst = Agent(
    name="risk_analyst",
    model="gemini-3.1-flash",
    description="Identifies and assesses risks.",
    instruction=(
        "Identify and assess the key risks for: {topic}. "
        "Cover financial, operational, regulatory, and reputational risks."
    ),
    output_key="risk_analysis",
)

analysis_team = ParallelAgent(
    name="analysis_team",
    description="Runs technical, market, and risk analysis concurrently.",
    sub_agents=[technical_analyst, market_analyst, risk_analyst],
)

synthesizer = Agent(
    name="synthesizer",
    model="gemini-3.1-flash",
    description="Synthesizes all analyses into a final recommendation.",
    instruction=(
        "You have three independent analyses. Synthesize them into a concise executive summary "
        "with a clear recommendation.\n\n"
        "Technical Analysis:\n{technical_analysis}\n\n"
        "Market Analysis:\n{market_analysis}\n\n"
        "Risk Analysis:\n{risk_analysis}"
    ),
    output_key="executive_summary",
)

# Wrap in SequentialAgent: run parallel analyses first, then synthesize
full_analysis = SequentialAgent(
    name="full_analysis_pipeline",
    description="Runs parallel analysis then synthesizes results.",
    sub_agents=[analysis_team, synthesizer],
)

runner = InMemoryRunner(agent=full_analysis, app_name="analysis_app")
session = runner.session_service.create_session(
    app_name="analysis_app",
    user_id="u1",
    state={"topic": "electric vehicle charging network expansion"},
)

for event in runner.run(
    user_id="u1",
    session_id=session.id,
    new_message=types.UserContent(
        parts=[types.Part(text="Analyze electric vehicle charging network expansion.")]
    ),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(part.text)
```

## 3. LoopAgent — Iterative Refinement

Repeats sub-agents until `exit_loop` tool is called or `max_iterations` is reached. The agent's instruction must include logic to call `exit_loop` when the quality bar is met.

```python
from google.adk import Agent, InMemoryRunner
from google.adk.agents import LoopAgent
from google.adk.tools import exit_loop
from google.genai import types


code_improver = Agent(
    name="code_improver",
    model="gemini-3.1-flash",
    description="Iteratively improves code quality until it meets the standard.",
    instruction=(
        "Review the code in session state under 'current_code'. "
        "If the code has no issues (correct, readable, no bugs), call exit_loop() to stop. "
        "Otherwise, rewrite the code with improvements and store it under 'current_code'. "
        "Improve only one category of issues per iteration: "
        "first correctness, then readability, then performance."
    ),
    tools=[exit_loop],
    output_key="current_code",
)

refinement_loop = LoopAgent(
    name="code_refinement_loop",
    description="Iteratively refines code until it meets quality standards or max iterations reached.",
    sub_agents=[code_improver],
    max_iterations=5,
)

runner = InMemoryRunner(agent=refinement_loop, app_name="refine_app")
session = runner.session_service.create_session(
    app_name="refine_app",
    user_id="u1",
    state={
        "current_code": "def add(a,b):\n  return a+b  # no type hints, no docstring"
    },
)

for event in runner.run(
    user_id="u1",
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="Improve this code.")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(part.text)

# Retrieve the refined code
final_session = runner.session_service.get_session(
    app_name="refine_app", user_id="u1", session_id=session.id
)
print(final_session.state.get("current_code"))
```

**Important:** If `exit_loop` is never called, the loop runs exactly `max_iterations` times then stops. Always instruct the agent on the condition for calling `exit_loop` to avoid wasted iterations.

> See `adk-agent-handoff.md` — covers agent routing via transfer_to_agent and output_key state passing rules for multi-agent workflows.

## 4. Composition Patterns

| Pattern | Use Case | Structure |
|---------|----------|-----------|
| Sequential | Pipeline (A outputs to B inputs to C) | `SequentialAgent(sub_agents=[a, b, c])` |
| Parallel | Gather independent perspectives concurrently | `ParallelAgent(sub_agents=[a, b, c])` |
| Parallel + Sequential | Fan-out then synthesize | `SequentialAgent([ParallelAgent([a, b, c]), synthesizer])` |
| Loop | Iterative refinement until quality met | `LoopAgent(sub_agents=[refiner], max_iterations=N)` |
| Handoff | Customer service / intent routing | Root with `sub_agents=[s1, s2]` + `tools=[transfer_to_agent]` |
| Loop inside Sequential | Refine one stage of a pipeline | `SequentialAgent([researcher, LoopAgent([refiner], max_iterations=3), publisher])` |

> See `adk-agent-handoff.md` for output_key state passing rules and examples.
