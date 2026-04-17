# Agentic AI Debugging Playbook

Common issues, diagnostic tools, and resolution patterns for LangGraph agents.

## 5 Most Common Issues

### 1. Infinite Loop / Max Iterations Reached

**Symptoms:** Agent hits `recursion_limit`, high iteration count, never produces final answer.

**Root Causes:**
- Missing or broken routing condition — agent always routes back to itself
- Tool always returns an error, causing agent to retry indefinitely
- LLM always produces tool calls, never a final response

**Diagnosis:**
```python
# Stream state updates to see where the agent loops
async for update in graph.astream(
    {"messages": [HumanMessage(content="test")]},
    config={"configurable": {"thread_id": "debug-001"}},
    stream_mode="updates",
):
    for node, state in update.items():
        print(f"[{node}] iteration={state.get('iteration_count', '?')}")
        if node == "agent":
            last_msg = state["messages"][-1] if state.get("messages") else None
            print(f"  tool_calls={getattr(last_msg, 'tool_calls', None)}")
```

**Fixes:**
1. Add iteration counter check in routing function
2. Add max error counter — after N tool errors, force END
3. Verify routing function returns END for non-tool-call responses
4. Check that tool results satisfy the agent's query

### 2. Hallucination / Incorrect Information

**Symptoms:** Agent confidently states incorrect facts, makes up data not in context.

**Root Causes:**
- No RAG grounding — relying on training data
- Retrieved documents are irrelevant
- System prompt doesn't enforce grounding
- Temperature too high

**Diagnosis:**
```python
# Check retrieved documents vs. generated answer
result = await graph.ainvoke(input, config)
docs = result.get("documents", [])
generation = result.get("generation", result["messages"][-1].content)

print(f"Documents retrieved: {len(docs)}")
for doc in docs:
    print(f"  - {doc['content'][:100]}...")
print(f"\nGeneration: {generation[:200]}")
print(f"\nGrounded: Check if generation references document content")
```

**Fixes:**
1. Add Self-RAG pattern with hallucination checking
2. Lower temperature to 0 for factual tasks
3. Add explicit system prompt: "Answer ONLY from the provided context"
4. Add document relevance grading before generation

### 3. Slow Response Times

**Symptoms:** Agent takes >30s, timeouts, poor user experience.

**Root Causes:**
- Too many LLM calls per invocation
- Using expensive model for simple tasks
- No streaming — waiting for full response
- Slow tools (database, API calls without timeout)

**Diagnosis:**
```python
import time

# Time each node execution
async for event in graph.astream_events(input, config, version="v2"):
    if event["event"] == "on_chain_start":
        print(f"[START] {event['name']} at {time.time():.2f}")
    elif event["event"] == "on_chain_end":
        print(f"[END]   {event['name']} at {time.time():.2f}")
    elif event["event"] == "on_chat_model_start":
        print(f"[LLM START] {event.get('name', '')} at {time.time():.2f}")
    elif event["event"] == "on_chat_model_end":
        print(f"[LLM END]   {event.get('name', '')} at {time.time():.2f}")
```

**Fixes:**
1. Use model routing — cheap model for simple tasks, expensive for complex
2. Enable streaming for user-facing responses
3. Add timeouts to all tool calls
4. Use prompt caching for long system prompts
5. Parallelize independent tool calls

### 4. Tool Failures

**Symptoms:** Tools return errors, agent can't complete task, error messages in responses.

**Root Causes:**
- API endpoint down or changed
- Missing authentication
- Invalid tool arguments from LLM
- Timeout on slow operations

**Diagnosis:**
```python
# Test tools in isolation
from my_agent_service.agents.tools.search import search_web

result = search_web.invoke({"query": "test query"})
print(f"Tool result: {result}")
print(f"Type: {type(result)}")
print(f"Length: {len(result)}")
```

**Fixes:**
1. Add retry with exponential backoff to tools
2. Add timeout to all I/O operations
3. Improve tool docstrings — LLM uses these to generate arguments
4. Add input validation with Pydantic `args_schema`
5. Return helpful error strings instead of empty results

### 5. Memory / State Loss

**Symptoms:** Agent doesn't remember previous turns, context is lost, repeated questions.

**Root Causes:**
- Not using checkpointer
- Using `MemorySaver` in production (not persistent)
- Wrong `thread_id` — each thread has separate state
- Message list not using `add_messages` annotation

**Diagnosis:**
```python
# Inspect checkpointed state
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpointer = AsyncPostgresSaver.from_conn_string(db_uri)
state = await checkpointer.aget({"configurable": {"thread_id": "thread-123"}})
if state:
    print(f"Messages in state: {len(state.values.get('messages', []))}")
    for msg in state.values["messages"]:
        print(f"  [{type(msg).__name__}] {msg.content[:100]}")
else:
    print("No state found for this thread_id")
```

**Fixes:**
1. Use `PostgresSaver` in production
2. Verify `thread_id` is consistent across requests
3. Ensure state uses `Annotated[list[BaseMessage], add_messages]`
4. Check that the checkpointer `setup()` was called at startup

## Debug Callback Handler

**File:** `src/<service>/observability/debug.py`

```python
from __future__ import annotations

from typing import Any

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import LLMResult

from ..core.logging import get_logger

logger = get_logger("debug")


class DebugCallbackHandler(AsyncCallbackHandler):
    """Verbose callback handler for debugging agent execution.

    Enable in development only — too noisy for production.
    """

    async def on_llm_start(self, serialized: dict, prompts: list[str], **kwargs: Any) -> None:
        model = serialized.get("kwargs", {}).get("model", "unknown")
        logger.debug("llm_start", model=model, prompt_count=len(prompts))

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for gen in response.generations:
            for g in gen:
                content = g.text[:200] if g.text else "[tool_calls]"
                logger.debug("llm_response", content=content)

    async def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("llm_error", error=str(error))

    async def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any) -> None:
        tool_name = serialized.get("name", "unknown")
        logger.debug("tool_start", tool=tool_name, input=input_str[:200])

    async def on_tool_end(self, output: str, **kwargs: Any) -> None:
        logger.debug("tool_end", output=output[:200])

    async def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        logger.error("tool_error", error=str(error))

    async def on_chat_model_start(self, serialized: dict, messages: list[list[BaseMessage]], **kwargs: Any) -> None:
        model = serialized.get("kwargs", {}).get("model", "unknown")
        msg_count = sum(len(batch) for batch in messages)
        logger.debug("chat_model_start", model=model, message_count=msg_count)


# Usage: pass as callback when invoking
# result = await graph.ainvoke(input, config={"callbacks": [DebugCallbackHandler()]})
```

## State Inspection Utilities

```python
def inspect_state(state: dict) -> None:
    """Print a human-readable summary of agent state."""
    print(f"\n{'='*60}")
    print(f"Thread: {state.get('thread_id', 'N/A')}")
    print(f"Iterations: {state.get('iteration_count', 0)}")
    print(f"Errors: {state.get('error_count', 0)}")
    print(f"Messages: {len(state.get('messages', []))}")

    for i, msg in enumerate(state.get("messages", [])):
        role = type(msg).__name__
        content = msg.content[:100] if msg.content else "[no content]"
        tool_calls = getattr(msg, "tool_calls", None)
        tool_info = f" (tools: {[tc['name'] for tc in tool_calls]})" if tool_calls else ""
        print(f"  [{i}] {role}: {content}{tool_info}")

    if state.get("documents"):
        print(f"\nDocuments: {len(state['documents'])}")
    if state.get("generation"):
        print(f"Generation: {state['generation'][:100]}")
    print(f"{'='*60}\n")
```

## LangSmith Trace Analysis

```python
from langsmith import Client


def analyze_trace(run_id: str) -> None:
    """Analyze a LangSmith trace for debugging."""
    client = Client()
    run = client.read_run(run_id)

    print(f"Run: {run.name}")
    print(f"Status: {run.status}")
    print(f"Latency: {run.total_tokens}ms")
    print(f"Tokens: input={run.prompt_tokens}, output={run.completion_tokens}")
    print(f"Cost: ${run.total_cost:.4f}")

    if run.error:
        print(f"Error: {run.error}")

    # Get child runs (individual LLM calls, tool executions)
    children = client.list_runs(parent_run_id=run_id)
    for child in children:
        print(f"  [{child.run_type}] {child.name}: {child.status} ({child.total_tokens}ms)")
```

## Quick Debugging Checklist

1. **Check the graph structure** — `graph.get_graph().draw_mermaid()` to visualize
2. **Stream updates** — `stream_mode="updates"` to see node-by-node execution
3. **Check state** — `inspect_state(result)` after invocation
4. **Check logs** — `LOG_LEVEL=debug` to see all structured log events
5. **Check LangSmith** — View trace for full execution timeline
6. **Test tools in isolation** — `tool.invoke({"arg": "value"})` directly
7. **Check checkpointer** — Verify state persistence with `aget()`
