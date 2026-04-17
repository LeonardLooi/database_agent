# ADK Core Patterns

## 1. Agent Configuration

Full `Agent(...)` constructor showing all key parameters:

```python
from google.adk import Agent
from google.genai import types
from pydantic import BaseModel


class AnalysisResult(BaseModel):
    summary: str
    confidence: float
    recommendations: list[str]


def search_web(query: str) -> str:
    """Search the web for information about the given query."""
    # implementation
    return f"Results for: {query}"


def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result."""
    # implementation
    return str(eval(expression))  # noqa: S307 — replace with safe eval in prod


analysis_agent = Agent(
    name="analysis_agent",
    model="gemini-3.1-flash",
    description="Analyzes data and produces structured analysis results.",
    instruction=(
        "You are a data analyst. Given the user's request, search for relevant "
        "information and produce a structured analysis. Always include a confidence "
        "score between 0.0 and 1.0 and at least one concrete recommendation."
    ),
    tools=[search_web, calculate],
    # Structured output: final response is parsed into AnalysisResult
    output_schema=AnalysisResult,
    # Stores the final structured output into session state under this key
    output_key="analysis_result",
    # Sub-agents this agent can hand off to (optional)
    sub_agents=[],
    # Callbacks (optional — see adk-tools-callbacks.md)
    before_model_callback=None,
    after_model_callback=None,
    on_model_error_callback=None,
    before_tool_callback=None,
    after_tool_callback=None,
    on_tool_error_callback=None,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
        ],
    ),
)
```

## 2. Runner Patterns

### InMemoryRunner (dev/testing — sync)

```python
from google.adk import InMemoryRunner
from google.genai import types

runner = InMemoryRunner(agent=analysis_agent, app_name="my_app")

# InMemoryRunner auto-creates a session; retrieve user_id and session_id
session = runner.session_service.create_session(
    app_name="my_app", user_id="user_001"
)

for event in runner.run(
    user_id=session.user_id,
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="Analyze renewable energy trends.")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(f"[{event.author}]: {part.text}")
```

### Runner with Production Session Service

```python
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
# For production: from google.adk.sessions import VertexAiSessionService
from google.genai import types

session_service = InMemorySessionService()
# Production: session_service = VertexAiSessionService(project_id="my-project", location="us-central1")

runner = Runner(
    app_name="my_app",
    agent=analysis_agent,
    session_service=session_service,
)

session = session_service.create_session(app_name="my_app", user_id="user_001")

for event in runner.run(
    user_id="user_001",
    session_id=session.id,
    new_message=types.UserContent(parts=[types.Part(text="Hello")]),
):
    if event.is_final_response() and event.content:
        for part in event.content.parts:
            if part.text:
                print(part.text)
```

### Async runner.run_async()

```python
import asyncio
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


async def run_agent(user_message: str) -> str:
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="my_app",
        agent=analysis_agent,
        session_service=session_service,
    )
    session = session_service.create_session(app_name="my_app", user_id="user_001")

    final_text = ""
    async for event in runner.run_async(
        user_id="user_001",
        session_id=session.id,
        new_message=types.UserContent(parts=[types.Part(text=user_message)]),
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    final_text += part.text
    return final_text


# asyncio.run(run_agent("Analyze solar energy adoption."))
```

### Debug Mode

```python
runner.run_debug(
    user_messages=["What are renewable energy trends?", "Summarize your findings."],
    user_id="user_001",
    session_id=session.id,
    verbose=True,
)
```

## 3. App Class

Use `App` when you need plugins, context caching, or resumability configuration:

```python
from google.adk import Runner
from google.adk.apps.app import App
from google.adk.sessions import InMemorySessionService

app = App(
    name="my_adk_app",
    root_agent=analysis_agent,
    # plugins=[...],                         # optional: ADK plugin list
    # context_cache_config=ContextCacheConfig(...),  # optional
    # resumability_config=ResumabilityConfig(...),   # optional
)

runner = Runner(
    app=app,
    session_service=InMemorySessionService(),
)
```

## 4. Session Management

```python
from google.adk.sessions import InMemorySessionService
# Production: from google.adk.sessions import VertexAiSessionService

session_service = InMemorySessionService()
# Production: session_service = VertexAiSessionService(project_id="my-project", location="us-central1")

# Create session with optional initial state
session = session_service.create_session(
    app_name="my_app",
    user_id="user_001",
    state={"user_tier": "premium", "language": "en"},
)

# Get session
existing_session = session_service.get_session(
    app_name="my_app",
    user_id="user_001",
    session_id=session.id,
)

# List sessions for a user
sessions = session_service.list_sessions(
    app_name="my_app",
    user_id="user_001",
)

# Delete session
session_service.delete_session(
    app_name="my_app",
    user_id="user_001",
    session_id=session.id,
)
```

> See `adk-structured-output.md` — covers session state access, structured output schemas, and UserContent construction patterns.
