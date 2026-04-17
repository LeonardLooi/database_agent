# ADK FastAPI Integration

## 1. Project Structure

```
src/
+-- main.py           # FastAPI app + runner init
+-- config.py         # Settings (pydantic-settings, GOOGLE_API_KEY)
+-- agents/
|   +-- my_agent.py   # Agent definitions
+-- tools/
|   +-- my_tools.py   # Tool functions
+-- api/
|   +-- routes.py     # Chat + stream endpoints
tests/
+-- test_agent.py     # InMemoryRunner unit tests
.env                  # GOOGLE_API_KEY=...
pyproject.toml
Dockerfile
```

## 2. Agent Definition Module

```python
# src/agents/my_agent.py
from google.adk import Agent
from ..tools.my_tools import get_weather


def build_agent() -> Agent:
    return Agent(
        name="my_assistant",
        model="gemini-3.1-flash",
        description="A helpful assistant",
        instruction="You are a helpful assistant. Use available tools to answer questions.",
        tools=[get_weather],
    )
```

Tool functions are plain Python functions with full docstrings. See `adk-tools-callbacks.md` for tool patterns.

## 3. Runner Initialization (main.py)

```python
# src/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from .agents.my_agent import build_agent
from .api.routes import router, set_runner

session_service = InMemorySessionService()
runner: Runner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    agent = build_agent()
    runner = Runner(
        app_name="my-adk-service",
        agent=agent,
        session_service=session_service,
    )
    set_runner(runner)
    yield
    if runner:
        await runner.close()


app = FastAPI(title="My ADK Service", lifespan=lifespan)
app.include_router(router, prefix="/api")
```

> **Runner Lifecycle Rule:** Always call `await runner.close()` in the lifespan shutdown to close MCP connections and release resources.

## 4. Request/Response Models

```python
# src/api/models.py
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    user_id: str
    session_id: str


class ChatResponse(BaseModel):
    message: str
    author: str
```

## 5. Routes — POST /chat (collect final response)

```python
# src/api/routes.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from google.adk import Runner
from google.genai import types
import structlog

from .models import ChatRequest, ChatResponse

logger = structlog.get_logger(__name__)
router = APIRouter()
_runner: Runner | None = None


def set_runner(r: Runner) -> None:
    global _runner
    _runner = r


@router.post("/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    if _runner is None:
        raise HTTPException(status_code=503, detail="Runner not initialized")
    try:
        async for event in _runner.run_async(
            user_id=request.user_id,
            session_id=request.session_id,
            new_message=types.UserContent(parts=[types.Part(text=request.message)]),
        ):
            if event.is_final_response() and event.content:
                text = "".join(
                    p.text or "" for p in event.content.parts if p.text
                )
                return ChatResponse(message=text, author=event.author)
    except Exception as exc:
        logger.error("chat_error", error=str(exc), user_id=request.user_id)
        raise HTTPException(status_code=500, detail="Agent error") from exc
    return ChatResponse(message="", author="agent")
```

## 6. Routes — GET /stream (SSE)

```python
@router.get("/stream")
async def stream_chat(message: str, user_id: str, session_id: str):
    if _runner is None:
        raise HTTPException(status_code=503, detail="Runner not initialized")

    async def generate():
        try:
            async for event in _runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.UserContent(parts=[types.Part(text=message)]),
            ):
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            yield f"data: {part.text}\n\n"
        except Exception as exc:
            logger.error("stream_error", error=str(exc), user_id=user_id)
            yield "data: [ERROR]\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

## 7. Session Creation Endpoint

```python
@router.post("/sessions")
async def create_session(user_id: str, session_id: str):
    if _runner is None:
        raise HTTPException(status_code=503, detail="Runner not initialized")
    await session_service.create_session(
        app_name="my-adk-service",
        user_id=user_id,
        session_id=session_id,
    )
    return {"session_id": session_id}
```

> Note: `session_service` must be imported from `main.py` or passed in via dependency injection.

## 8. Error Handling

- Wrap every `runner.run_async()` call in `try/except Exception`
- Log with `structlog` — include `user_id` and `session_id` in every log record
- Raise `HTTPException(status_code=500, detail="Agent error")` — never leak internal error messages
- For SSE streams: emit `data: [ERROR]\n\n` before closing the generator so the client can detect failures

```python
except Exception as exc:
    logger.error("agent_error", error=str(exc), user_id=user_id, session_id=session_id)
    raise HTTPException(status_code=500, detail="Agent error") from exc
```

## 9. Production: VertexAiSessionService

Switch from `InMemorySessionService` to `VertexAiSessionService` for persistent sessions in production:

```python
from google.adk.sessions import VertexAiSessionService

session_service = VertexAiSessionService(
    project="my-gcp-project",
    location="us-central1",
)
```

All other code (Runner init, routes) stays the same — the session service is the only swap.

## 10. Adding Memory

```python
from google.adk.memory import InMemoryMemoryService
from google.adk.tools import load_memory, preload_memory

memory_service = InMemoryMemoryService()

runner = Runner(
    app_name="my-adk-service",
    agent=agent,
    session_service=session_service,
    memory_service=memory_service,
)

# In agent definition, add built-in memory tools:
agent = Agent(
    name="my_assistant",
    model="gemini-3.1-flash",
    instruction="...",
    tools=[load_memory, preload_memory, get_weather],
)
```
