# Agentic AI Core Templates

## FastAPI Application Entry Point

**File:** `src/<service>/main.py`

```python
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .api.middleware.request_context import RequestContextMiddleware
from .api.routes import agent, health
from .core.config import settings
from .core.logging import get_logger, setup_logging
from .llm.providers import LLMProviderFactory
from .observability.metrics import setup_prometheus

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Initialize and clean up application resources."""
    setup_logging()
    logger.info("starting_application", app_name=settings.app_name, env=settings.app_env)

    # Initialize LLM providers
    provider_factory = LLMProviderFactory()
    app.state.provider_factory = provider_factory

    # Initialize checkpointer
    checkpointer = AsyncPostgresSaver.from_conn_string(settings.checkpoint_db_uri)
    await checkpointer.setup()
    app.state.checkpointer = checkpointer

    # Setup Prometheus
    setup_prometheus(app)

    logger.info("application_ready")
    yield

    # Shutdown
    logger.info("shutting_down_application")
    # Close checkpointer connection pool
    # Close any open provider connections


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url=None,
)

# Middleware
app.add_middleware(RequestContextMiddleware)

# Routes
app.include_router(agent.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
```

## Agent Routes

**File:** `src/<service>/api/routes/agent.py`

```python
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage

from ...core.exceptions import AgentError, LLMProviderError
from ...core.logging import get_logger
from ...models.schemas import AgentRequest, AgentResponse

logger = get_logger(__name__)

router = APIRouter(tags=["agent"])


def get_graph(request: Request):
    """Dependency: get compiled agent graph from app state."""
    return request.app.state.agent_graph


@router.post("/agent/invoke", response_model=AgentResponse)
async def invoke_agent(
    request: AgentRequest,
    graph=Depends(get_graph),
) -> AgentResponse:
    """Invoke the agent and return the final response."""
    logger.info("agent_invoke", thread_id=request.thread_id, message_length=len(request.message))

    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content=request.message)]},
            config={
                "configurable": {"thread_id": request.thread_id},
                "recursion_limit": request.max_iterations or 25,
            },
        )
        final_message = result["messages"][-1]
        content = final_message.content if isinstance(final_message, AIMessage) else str(final_message)

        return AgentResponse(
            thread_id=request.thread_id,
            message=content,
            iteration_count=result.get("iteration_count", 0),
        )

    except LLMProviderError as e:
        logger.error("provider_error", error=str(e), thread_id=request.thread_id)
        raise HTTPException(status_code=502, detail=f"LLM provider error: {e}")
    except AgentError as e:
        logger.error("agent_error", error=str(e), thread_id=request.thread_id)
        raise HTTPException(status_code=500, detail=f"Agent error: {e}")
    except Exception as e:
        logger.error("invoke_failed", error=str(e), thread_id=request.thread_id)
        raise HTTPException(status_code=500, detail="Agent invocation failed")


@router.post("/agent/stream")
async def stream_agent(
    request: AgentRequest,
    graph=Depends(get_graph),
) -> StreamingResponse:
    """Stream agent responses as Server-Sent Events."""

    async def event_generator():
        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=request.message)]},
                config={
                    "configurable": {"thread_id": request.thread_id},
                    "recursion_limit": request.max_iterations or 25,
                },
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {content}\n\n"

                elif kind == "on_tool_start":
                    tool_name = event["name"]
                    yield f"event: tool_start\ndata: {tool_name}\n\n"

                elif kind == "on_tool_end":
                    yield f"event: tool_end\ndata: {event['name']}\n\n"

            yield "event: done\ndata: [DONE]\n\n"

        except Exception as e:
            logger.error("stream_failed", error=str(e), thread_id=request.thread_id)
            yield f"event: error\ndata: {e}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
```

## Health Check Route

**File:** `src/<service>/api/routes/health.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Request

from ...core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check endpoint — verify all dependencies are reachable."""
    checks: dict[str, str] = {}

    # Check LLM provider
    try:
        factory = request.app.state.provider_factory
        llm = factory.get_default()
        await llm.ainvoke([{"role": "user", "content": "ping"}])
        checks["llm"] = "healthy"
    except Exception as e:
        checks["llm"] = f"unhealthy: {e}"

    # Check checkpointer (PostgreSQL)
    try:
        checkpointer = request.app.state.checkpointer
        # Attempt a lightweight operation
        checks["checkpoint_db"] = "healthy"
    except Exception as e:
        checks["checkpoint_db"] = f"unhealthy: {e}"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"

    return {"status": overall, "checks": checks}
```

## Request Context Middleware

**File:** `src/<service>/api/middleware/request_context.py`

```python
from __future__ import annotations

import uuid
from contextvars import ContextVar

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# Context variable for correlation ID — accessible anywhere in the async call chain
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Inject correlation ID into every request for distributed tracing."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Use incoming header or generate new ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id_var.set(request_id)

        # Bind to structlog context for automatic inclusion in all log entries
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

## Base State Schemas

**File:** `src/<service>/agents/state.py`

```python
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Base state for a single-agent graph.

    Fields:
        messages: Conversation history with automatic message merging.
        iteration_count: Loop counter — checked in routing to prevent infinite loops.
        error_count: Tracks consecutive errors for fallback decisions.
        thread_id: Conversation thread identifier for checkpointing.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    iteration_count: int
    error_count: int
    thread_id: str


class RAGState(AgentState):
    """Extended state for RAG-enabled agents.

    Additional Fields:
        query: The user's original query (may differ from last message).
        documents: Retrieved documents for context.
        generation: The RAG-generated answer.
        is_grounded: Whether the generation is supported by documents.
    """

    query: str
    documents: list[dict[str, Any]]
    generation: str
    is_grounded: bool


class MultiAgentState(AgentState):
    """Extended state for multi-agent collaborative graphs.

    Additional Fields:
        current_agent: Name of the agent currently processing.
        agent_outputs: Accumulated outputs from each specialist agent.
        task_plan: Decomposed sub-tasks for delegation.
        completed_tasks: Sub-tasks that have been completed.
    """

    current_agent: str
    agent_outputs: dict[str, str]
    task_plan: list[str]
    completed_tasks: list[str]
```

## Request/Response Models

**File:** `src/<service>/models/schemas.py`

```python
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request body for agent invocation."""

    message: str = Field(..., min_length=1, max_length=100_000, description="User message to the agent")
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Conversation thread ID")
    max_iterations: int | None = Field(default=None, ge=1, le=100, description="Override max iterations")


class AgentResponse(BaseModel):
    """Response body from agent invocation."""

    thread_id: str
    message: str
    iteration_count: int = 0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    checks: dict[str, str]
```
