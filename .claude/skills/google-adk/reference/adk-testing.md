# ADK Testing Patterns

## 1. Test Dependencies

```toml
# pyproject.toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

> All ADK tests are async — `asyncio_mode = "auto"` removes the need for `@pytest.mark.asyncio` on every test.

## 2. InMemoryRunner for Unit Tests

`InMemoryRunner` is the only approved runner for unit tests. It does not call the real Gemini API.

```python
# tests/test_agent.py
import pytest
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.agents.my_agent import build_agent


@pytest.fixture
def runner():
    agent = build_agent()
    return InMemoryRunner(agent=agent, app_name="test_app")


async def test_basic_response(runner):
    events = []
    async for event in runner.run_async(
        user_id="test_user",
        session_id="test_session",
        new_message=types.UserContent(parts=[types.Part(text="Hello")]),
    ):
        if event.is_final_response():
            events.append(event)

    assert len(events) > 0
    assert events[0].content is not None
```

## 3. Debug Mode for Quick Tests

`run_debug` collects all events and returns them as a list. Use for exploratory tests or CI smoke checks.

```python
async def test_with_debug(runner):
    events = await runner.run_debug(
        user_messages=["What is 2+2?"],
        user_id="debug_user",
        session_id="debug_session",
        verbose=True,
    )
    assert any(e.is_final_response() for e in events)
```

## 4. Testing Tools Directly

Tool functions are plain Python — test them without a runner. No mocking required for pure logic.

```python
from src.tools.my_tools import get_weather


def test_get_weather_returns_city_name():
    result = get_weather("Paris")
    assert "Paris" in result
    assert isinstance(result, str)
```

## 5. Testing Tools with ToolContext (State)

Use `MagicMock(spec=ToolContext)` to simulate state injection.

```python
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from src.tools.cart_tools import add_to_cart


def test_stateful_tool_writes_state():
    mock_ctx = MagicMock(spec=ToolContext)
    mock_ctx.state = {}

    result = add_to_cart("apple", 2, mock_ctx)

    assert "apple" in result
    assert mock_ctx.state["cart"] == [{"item": "apple", "quantity": 2}]
```

## 6. Testing Sequential Pipelines

Check `event.author` to confirm the correct agent in the pipeline produced the final response.

```python
from google.adk.agents import SequentialAgent
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types


@pytest.fixture
def pipeline_runner():
    researcher = Agent(
        name="researcher",
        model="gemini-3.1-flash",
        instruction="Summarize the topic in one sentence. Output stored in state key 'summary'.",
        output_key="summary",
    )
    writer = Agent(
        name="writer",
        model="gemini-3.1-flash",
        instruction="Expand on this summary: {summary}",
    )
    pipeline = SequentialAgent(
        name="research_pipeline",
        sub_agents=[researcher, writer],
    )
    return InMemoryRunner(agent=pipeline, app_name="test_pipeline")


async def test_sequential_pipeline_final_author(pipeline_runner):
    final_events = []
    async for event in pipeline_runner.run_async(
        user_id="u1",
        session_id="s1",
        new_message=types.UserContent(parts=[types.Part(text="Explain quantum computing")]),
    ):
        if event.is_final_response():
            final_events.append(event)

    assert len(final_events) > 0
    # The last agent in the pipeline should be the author of the final response
    assert final_events[-1].author == "writer"
```

## 7. Testing Callbacks

Patch callbacks by replacing the agent attribute before invoking `run_async`.

```python
from unittest.mock import AsyncMock
from google.genai import types


async def test_before_model_callback_is_invoked(runner):
    called = []

    async def spy_callback(ctx, request):
        called.append(True)
        return None  # returning None lets the model call proceed

    runner.agent.before_model_callback = [spy_callback]

    async for _ in runner.run_async(
        user_id="u1",
        session_id="s1",
        new_message=types.UserContent(parts=[types.Part(text="Hello")]),
    ):
        pass

    assert len(called) > 0
```

## 8. FastAPI Integration Test

Use `httpx.AsyncClient` with `ASGITransport` — no real server needed.

```python
import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from src.main import app


async def test_chat_endpoint_returns_200():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/chat",
            json={
                "message": "Hello",
                "user_id": "u1",
                "session_id": "s1",
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert "message" in body
    assert "author" in body


async def test_stream_endpoint_returns_sse():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        async with client.stream(
            "GET",
            "/api/stream",
            params={"message": "Hi", "user_id": "u1", "session_id": "s1"},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            chunks = []
            async for line in response.aiter_lines():
                chunks.append(line)
            assert any("[DONE]" in c for c in chunks)
```

## 9. Test Checklist

- [ ] Basic agent response (happy path) — `test_basic_response`
- [ ] Tool called when expected — mock or assert on tool return value
- [ ] State written/read correctly via ToolContext — `MagicMock(spec=ToolContext)`
- [ ] Sequential pipeline produces output at each stage — check `event.author`
- [ ] LoopAgent exits within `max_iterations` — confirm no infinite loop
- [ ] Callback intercepted model call — spy on `before_model_callback`
- [ ] Error scenario returns structured error (not exception) — assert on error response body
- [ ] FastAPI `/chat` endpoint returns 200 with `message` field
- [ ] FastAPI `/stream` endpoint returns SSE ending in `[DONE]`

## 10. What NOT to Do in Tests

- **Never call the real Gemini API** in unit tests — use `InMemoryRunner` only
- **Never skip `asyncio_mode = "auto"`** — async tests silently pass without it
- **Never test tool state** by reading `tool_context.state` after `run_async` — test tools directly with a mock context instead
- **Never assert on exact model output text** — model responses are non-deterministic; assert on structure (not None, contains key, status code)
