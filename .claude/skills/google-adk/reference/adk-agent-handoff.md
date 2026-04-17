# ADK Agent Handoff and output_key Rules

## 1. Agent Handoff (transfer_to_agent)

The root agent routes to specialist sub-agents using the built-in `transfer_to_agent` tool. Sub-agents are listed in `sub_agents` on the root. Each sub-agent also carries `tools=[transfer_to_agent]` to allow further handoff.

```python
from google.adk import Agent, InMemoryRunner
from google.adk.tools import transfer_to_agent
from google.genai import types


billing_agent = Agent(
    name="billing_agent",
    model="gemini-3.1-flash",
    description="Handles billing questions, invoice issues, and payment disputes.",
    instruction=(
        "You are a billing specialist. Help the user with any billing-related questions: "
        "invoices, payments, refunds, and subscription changes. "
        "If the question is technical (not billing), transfer back to the router."
    ),
    tools=[transfer_to_agent],
)

technical_agent = Agent(
    name="technical_agent",
    model="gemini-3.1-flash",
    description="Handles technical support, bugs, and product usage questions.",
    instruction=(
        "You are a technical support specialist. Help the user with technical issues: "
        "bugs, setup problems, API questions, and feature usage. "
        "If the question is about billing, transfer back to the router."
    ),
    tools=[transfer_to_agent],
)

router_agent = Agent(
    name="router_agent",
    model="gemini-3.1-flash",
    description="Routes customer service requests to the correct specialist.",
    instruction=(
        "You are a customer service router. "
        "For billing questions (invoices, payments, refunds), transfer to billing_agent. "
        "For technical questions (bugs, setup, API), transfer to technical_agent. "
        "Greet the user and route immediately — do not attempt to answer specialist questions yourself."
    ),
    sub_agents=[billing_agent, technical_agent],
    tools=[transfer_to_agent],
)

runner = InMemoryRunner(agent=router_agent, app_name="support_app")
session = runner.session_service.create_session(app_name="support_app", user_id="u1")

for event in runner.run(
    user_id="u1",
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="I have a question about my invoice.")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(f"[{event.author}]: {part.text}")
```

---

## 2. output_key State Passing Rules

- Each sub-agent sets `output_key="key_name"` — ADK stores the agent's final text response in session state under that key after the agent completes.
- Downstream agents reference it as `{key_name}` inside their `instruction` string — ADK performs the substitution at runtime from session state.
- State is dict-like; tools and callbacks can also read it via `tool_context.state["key_name"]` or `callback_context.state["key_name"]`.
- Only set `output_key` when the agent's output is needed downstream. Agents that produce final user-facing output do not need `output_key`.
- Keys must be unique across all agents in the same pipeline to avoid overwriting.
- `output_key` stores plain text. If `output_schema` is also set, the stored value is the model's raw JSON string — parse with `Model.model_validate_json(value)`.

```python
# output_key in a SequentialAgent pipeline — correct pattern
stage_a = Agent(
    name="stage_a",
    model="gemini-3.1-flash",
    instruction="Produce a summary of the topic.",
    output_key="stage_a_output",          # stored to state["stage_a_output"]
)

stage_b = Agent(
    name="stage_b",
    model="gemini-3.1-flash",
    instruction="Expand on this summary: {stage_a_output}",  # read from state
    output_key="stage_b_output",
)

pipeline = SequentialAgent(name="pipeline", sub_agents=[stage_a, stage_b])
```
