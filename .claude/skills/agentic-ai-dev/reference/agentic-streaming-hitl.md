# Agentic AI Streaming & Human-in-the-Loop

Patterns for real-time token streaming and human approval workflows in LangGraph agents.

## Token Streaming

Stream individual tokens as the LLM generates them.

```python
from langchain_core.messages import HumanMessage


async def stream_tokens(graph, message: str, thread_id: str):
    """Stream tokens from agent using astream with messages mode."""
    config = {"configurable": {"thread_id": thread_id}}

    async for chunk in graph.astream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode="messages",
    ):
        # chunk is a tuple: (message_chunk, metadata)
        msg, metadata = chunk
        if msg.content and metadata.get("langgraph_node") == "agent":
            print(msg.content, end="", flush=True)
```

## Event Streaming

Rich event stream with tool start/end, node transitions, and token chunks.

```python
async def stream_events(graph, message: str, thread_id: str):
    """Stream all events from agent execution."""
    config = {"configurable": {"thread_id": thread_id}}

    async for event in graph.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            # Token-level streaming
            content = event["data"]["chunk"].content
            if content:
                yield {"type": "token", "content": content}

        elif kind == "on_chat_model_start":
            yield {"type": "llm_start", "model": event.get("name", "")}

        elif kind == "on_chat_model_end":
            yield {"type": "llm_end"}

        elif kind == "on_tool_start":
            yield {"type": "tool_start", "tool": event["name"], "input": event["data"].get("input")}

        elif kind == "on_tool_end":
            yield {"type": "tool_end", "tool": event["name"], "output": str(event["data"].get("output", ""))[:200]}

        elif kind == "on_chain_start" and event.get("name"):
            yield {"type": "node_start", "node": event["name"]}

        elif kind == "on_chain_end" and event.get("name"):
            yield {"type": "node_end", "node": event["name"]}
```

## State Update Streaming

Stream state updates as each node completes — useful for progress tracking.

```python
async def stream_state_updates(graph, message: str, thread_id: str):
    """Stream state updates after each node execution."""
    config = {"configurable": {"thread_id": thread_id}}

    async for update in graph.astream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode="updates",
    ):
        # update is a dict: {node_name: state_update}
        for node_name, state_update in update.items():
            print(f"[{node_name}] updated keys: {list(state_update.keys())}")
```

## FastAPI SSE Integration

**File:** `src/<service>/api/routes/stream.py`

```python
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from ...core.logging import get_logger
from ...models.schemas import AgentRequest

logger = get_logger(__name__)

router = APIRouter(tags=["streaming"])


@router.post("/agent/stream")
async def stream_agent(request: AgentRequest, graph=Depends(get_graph)) -> StreamingResponse:
    """Stream agent responses as Server-Sent Events (SSE).

    Event types:
    - data: Token content
    - tool_start: Tool invocation began
    - tool_end: Tool invocation completed
    - done: Stream complete
    - error: Error occurred
    """

    async def sse_generator():
        try:
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=request.message)]},
                config={
                    "configurable": {"thread_id": request.thread_id},
                    "recursion_limit": 25,
                },
                version="v2",
            ):
                kind = event["event"]

                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"

                elif kind == "on_tool_start":
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['name']})}\n\n"

                elif kind == "on_tool_end":
                    output = str(event["data"].get("output", ""))[:200]
                    yield f"data: {json.dumps({'type': 'tool_end', 'tool': event['name'], 'output': output})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error("stream_error", error=str(e), thread_id=request.thread_id)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

## Human-in-the-Loop (HITL)

### Basic Approval Workflow

Use `interrupt_before` to pause execution and wait for human approval.

```python
from langgraph.graph import StateGraph, END
from langgraph.types import Command


def build_hitl_agent(provider_factory, checkpointer):
    """Agent that pauses for human approval before executing dangerous tools."""

    tools = [search_tool, delete_tool]  # delete_tool requires approval
    llm = provider_factory.get_default().bind_tools(tools)

    async def agent_node(state: AgentState) -> dict:
        response = await llm.ainvoke(state["messages"])
        return {"messages": [response], "iteration_count": state["iteration_count"] + 1}

    async def approval_node(state: AgentState) -> dict:
        """This node is interrupted — execution pauses here for human input."""
        # When resumed, the human's approval/rejection is in the latest message
        last_message = state["messages"][-1]
        if hasattr(last_message, 'content') and "approved" in last_message.content.lower():
            return {}  # Continue to tool execution
        return {"messages": [AIMessage(content="Action cancelled by user.")]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("approval", approval_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("approval", "tools")
    graph.add_edge("tools", "agent")

    # Interrupt BEFORE the approval node — graph pauses here
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["approval"],
    )
```

### Resuming After Approval

```python
# Step 1: Invoke — graph pauses at approval node
config = {"configurable": {"thread_id": "thread-123"}}
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="Delete all old records")]},
    config=config,
)
# result shows the agent wants to use delete_tool

# Step 2: Human reviews and approves
# Resume with approval message
result = await graph.ainvoke(
    {"messages": [HumanMessage(content="Approved")]},
    config=config,
)
# Graph continues from where it paused
```

### Approval with Timeout and Escalation

```python
import asyncio
from datetime import datetime, timezone


class ApprovalManager:
    """Manage human approvals with timeout and escalation."""

    def __init__(self, timeout_seconds: int = 300):
        self._pending: dict[str, asyncio.Event] = {}
        self._decisions: dict[str, bool] = {}
        self._timeout = timeout_seconds

    async def request_approval(self, thread_id: str, action: str, details: str) -> bool:
        """Request human approval with timeout.

        Returns:
            True if approved, False if rejected or timed out.
        """
        event = asyncio.Event()
        self._pending[thread_id] = event

        logger.info("approval_requested", thread_id=thread_id, action=action)

        # Notify human (webhook, email, Slack, etc.)
        await self._notify_human(thread_id, action, details)

        try:
            await asyncio.wait_for(event.wait(), timeout=self._timeout)
            approved = self._decisions.get(thread_id, False)
            logger.info("approval_decision", thread_id=thread_id, approved=approved)
            return approved
        except asyncio.TimeoutError:
            logger.warning("approval_timeout", thread_id=thread_id)
            await self._escalate(thread_id, action)
            return False
        finally:
            self._pending.pop(thread_id, None)
            self._decisions.pop(thread_id, None)

    def submit_decision(self, thread_id: str, approved: bool) -> None:
        """Submit a human decision for a pending approval."""
        self._decisions[thread_id] = approved
        event = self._pending.get(thread_id)
        if event:
            event.set()

    async def _notify_human(self, thread_id: str, action: str, details: str) -> None:
        """Send notification to human reviewer."""
        # Implement: Slack webhook, email, push notification, etc.
        pass

    async def _escalate(self, thread_id: str, action: str) -> None:
        """Escalate when approval times out."""
        logger.warning("approval_escalated", thread_id=thread_id, action=action)
        # Implement: Notify manager, create ticket, etc.
```

## Streaming Mode Selection Guide

| Mode | Use Case | What You Get |
|------|----------|-------------|
| `stream_mode="messages"` | Chat UIs | Token-by-token streaming |
| `stream_mode="updates"` | Progress bars | Node completion updates |
| `stream_mode="values"` | Debugging | Full state after each step |
| `astream_events(v2)` | Rich UIs | All events (tokens, tools, nodes) |

## Key Rules

| Rule | Standard |
|------|----------|
| SSE format | Always use `data: {json}\n\n` format |
| Error events | Stream errors as events, don't break the connection |
| HITL | Use `interrupt_before` for approval, never `interrupt_after` |
| Checkpointing | HITL requires a checkpointer — state must persist while waiting |
| Timeouts | Always set approval timeouts — never block indefinitely |
| Buffering | Disable proxy buffering (`X-Accel-Buffering: no`) |
