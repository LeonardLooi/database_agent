# ADK Structured Output and Session State

> **Forwarding note:** This file was separated from `adk-core-patterns.md` to keep reference files under 300 lines. It covers the latter half of core patterns: session state access, structured output, and UserContent construction.

## 1. Session State Access

Tools access and mutate session state via `ToolContext`:

```python
from google.adk.tools import ToolContext


def update_user_preference(preference_key: str, preference_value: str, tool_context: ToolContext) -> str:
    """Store a user preference into session state.

    Args:
        preference_key: The preference name (e.g. 'theme', 'language').
        preference_value: The value to store.
        tool_context: Injected by ADK — provides session state access.

    Returns:
        Confirmation message.
    """
    # Read existing value (returns None if not set)
    existing = tool_context.state.get(preference_key)

    # Write new value — immediately visible to subsequent tool calls in this turn
    tool_context.state[preference_key] = preference_value

    if existing is not None:
        return f"Updated {preference_key} from '{existing}' to '{preference_value}'."
    return f"Set {preference_key} to '{preference_value}'."


def get_user_context(tool_context: ToolContext) -> dict:
    """Return all current session state values for context.

    Args:
        tool_context: Injected by ADK — provides session state access.

    Returns:
        Dict of all current session state entries.
    """
    return dict(tool_context.state)
```

Callbacks also access state via `callback_context.state` (same interface):

```python
from google.adk.agents.callback_context import CallbackContext


def log_model_call(callback_context: CallbackContext, llm_request) -> None:
    user_tier = callback_context.state.get("user_tier", "standard")
    # log or modify based on tier
```

## 2. Structured Output

Define a Pydantic model as `output_schema`; ADK instructs the model to respond in that schema. Use `output_key` to store the result in session state for downstream agents.

```python
from pydantic import BaseModel, Field
from google.adk import Agent, InMemoryRunner
from google.genai import types
import json


class ResearchReport(BaseModel):
    title: str = Field(description="Concise title for the report")
    key_findings: list[str] = Field(description="Top 3-5 findings")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")
    next_steps: list[str] = Field(description="Recommended actions")


research_agent = Agent(
    name="research_agent",
    model="gemini-3.1-flash",
    instruction="Research the topic and produce a structured report.",
    output_schema=ResearchReport,
    output_key="research_report",  # stored in session state under this key
)

runner = InMemoryRunner(agent=research_agent, app_name="research_app")
session = runner.session_service.create_session(app_name="research_app", user_id="u1")

response_text = ""
for event in runner.run(
    user_id="u1",
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="Research quantum computing trends.")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                response_text += part.text

# Parse the structured output
report = ResearchReport.model_validate_json(response_text)
print(report.title)
print(report.confidence)

# Also available in session state (for SequentialAgent pipelines)
final_session = runner.session_service.get_session(
    app_name="research_app", user_id="u1", session_id=session.id
)
stored_report = final_session.state.get("research_report")
```

## 3. UserContent Construction

```python
from google.genai import types

# Simple text message
new_message = types.UserContent(parts=[types.Part(text="Hello, how can you help me?")])

# Multi-part message (text + inline data)
multi_part_message = types.UserContent(
    parts=[
        types.Part(text="Analyze this image:"),
        types.Part(inline_data=types.Blob(mime_type="image/png", data=b"...")),
    ]
)

# Pass to runner
runner.run(
    user_id="user_001",
    session_id=session.id,
    new_message=new_message,
)
```
