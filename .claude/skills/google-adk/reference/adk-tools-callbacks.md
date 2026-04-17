# ADK Callbacks

> See `adk-tools-basic.md` — covers plain functions, ToolContext injection, async tools, Pydantic input models, FunctionTool with confirmation, built-in tools reference, and McpToolset integration.

## 1. before_model_callback

Called before each LLM request. Return `None` to continue; return an `LlmResponse`
to short-circuit (the model is never called).

```python
from google.adk.agents import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Optional
import time

async def rate_limit_check(
    ctx: CallbackContext, request: LlmRequest
) -> Optional[LlmResponse]:
    """Block requests that exceed the per-minute rate limit."""
    call_times: list = ctx.state.get("model_call_times", [])
    now = time.monotonic()
    call_times = [t for t in call_times if now - t < 60]

    if len(call_times) >= 10:
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="Rate limit reached. Please wait a moment.")],
            )
        )

    call_times.append(now)
    ctx.state["model_call_times"] = call_times
    return None  # continue to model
```

---

## 2. after_model_callback

Called after a successful LLM response. Return `None` to use the original response;
return a new `LlmResponse` to replace it.

```python
import structlog
from google.adk.agents import CallbackContext
from google.adk.models.llm_response import LlmResponse
from typing import Optional

log = structlog.get_logger()

async def log_response(
    ctx: CallbackContext, response: LlmResponse
) -> Optional[LlmResponse]:
    """Log response metadata for observability."""
    text_parts = [
        p.text for p in (response.content.parts or []) if hasattr(p, "text")
    ]
    log.info(
        "model_response",
        session_id=ctx.session_id,
        part_count=len(text_parts),
        total_chars=sum(len(t) for t in text_parts),
    )
    return None  # keep original response unchanged
```

---

## 3. on_model_error_callback

Called when the LLM request raises an exception. Return an `LlmResponse` to
recover gracefully, or return `None` to let the error propagate.

```python
import structlog
from google.adk.agents import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Optional

log = structlog.get_logger()

async def handle_model_error(
    ctx: CallbackContext, request: LlmRequest, error: Exception
) -> Optional[LlmResponse]:
    """Return a safe fallback response on model failure."""
    log.error("model_call_failed", error=str(error), session_id=ctx.session_id)
    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text="I encountered an error. Please try again.")],
        )
    )
```

---

## 4. Tool Callbacks — before, after, and on_error

All three tool callbacks share the same signature shape. Use them for
validation, logging, and error recovery around tool execution.

```python
import structlog
from google.adk.tools import BaseTool, ToolContext
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from typing import Any, Optional

log = structlog.get_logger()

# --- before_tool_callback ---
# Return None to allow the call; return a dict to override the result entirely.
async def validate_tool_args(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
) -> Optional[dict]:
    """Reject delete operations in read-only sessions."""
    if tool.name.startswith("delete_") and tool_context.state.get("read_only"):
        return {"error": "Delete operations are disabled in read-only mode."}
    return None  # proceed normally

# --- after_tool_callback ---
# Return None to use the original result; return a dict to replace it.
async def log_tool_result(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, result: dict
) -> Optional[dict]:
    """Log every tool invocation with its outcome."""
    log.info("tool_completed", tool_name=tool.name, args=args, result=result)
    return None  # keep original result

# --- on_tool_error_callback ---
# Return a dict to recover; return None to let the error propagate.
async def handle_tool_error(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, error: Exception
) -> Optional[dict]:
    """Log and return a structured error payload instead of raising."""
    log.error("tool_failed", tool_name=tool.name, args=args, error=str(error))
    return {"error": f"Tool '{tool.name}' failed: {error}", "success": False}
```

---

## 5. Attaching Callbacks to Agent

```python
from google.adk import Agent

agent = Agent(
    name="my_agent",
    model="gemini-3.1-flash",
    instruction="You are a helpful assistant.",
    tools=[get_weather, remember_preference],
    before_model_callback=[rate_limit_check],   # list — multiple callbacks supported
    after_model_callback=log_response,           # single callback also works
    on_model_error_callback=handle_model_error,
    before_tool_callback=validate_tool_args,
    after_tool_callback=log_tool_result,
    on_tool_error_callback=handle_tool_error,
)
```

**Imports summary:**

```python
from google.adk import Agent, Runner
from google.adk.agents import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from typing import Any, Optional
```
