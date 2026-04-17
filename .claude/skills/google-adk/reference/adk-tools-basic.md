# ADK Tools — Basic Patterns

## 1. Plain Function Tool (auto-schema)

ADK auto-wraps plain Python functions as tools. The docstring — including `Args` and
`Returns` sections — is used to generate the tool schema that the model sees.

```python
def get_weather(city: str, unit: str = "celsius") -> dict:
    """Get current weather for a city.

    Args:
        city: The name of the city to look up.
        unit: Temperature unit, either 'celsius' or 'fahrenheit'.

    Returns:
        A dict with keys 'temperature' (float), 'condition' (str),
        and 'humidity' (int).
    """
    # implementation
    return {"temperature": 22.5, "condition": "sunny", "humidity": 60}
```

Pass the function directly to `Agent(tools=[get_weather])` — no wrapper required.

---

## 2. Tool with ToolContext (State Access)

Add a `tool_context: ToolContext` parameter to any tool function. ADK injects it
automatically at call time — callers never pass it.

```python
from google.adk.tools import ToolContext

def remember_preference(key: str, value: str, tool_context: ToolContext) -> dict:
    """Store a user preference in session state.

    Args:
        key: Preference name to store.
        value: Value to associate with the key.
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'stored' bool and 'key' str.
    """
    existing = tool_context.state.get(key, None)
    tool_context.state[key] = value
    return {"stored": True, "key": key, "previous": existing}
```

Read: `tool_context.state.get("key", default)`
Write: `tool_context.state["key"] = value`

---

## 3. Async Tool

Use `async def` for tools that perform I/O. ADK awaits them automatically.

```python
import asyncio
from google.adk.tools import ToolContext

async def fetch_report(report_id: str, tool_context: ToolContext) -> dict:
    """Fetch a report from the external reporting service.

    Args:
        report_id: The unique ID of the report to fetch.
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'report_id' str and 'data' dict.
    """
    await asyncio.sleep(0.1)  # simulates async I/O
    cached = tool_context.state.get(f"report:{report_id}")
    if cached:
        return {"report_id": report_id, "data": cached, "source": "cache"}
    # ... real fetch here
    return {"report_id": report_id, "data": {}, "source": "api"}
```

---

## 4. Pydantic Input Tool

For structured inputs, define a `BaseModel` and use it as the parameter type.
ADK extracts the schema from the model for the tool definition.

```python
from pydantic import BaseModel
from google.adk.tools import ToolContext

class OrderRequest(BaseModel):
    product_id: str
    quantity: int
    shipping_address: str

def place_order(order: OrderRequest, tool_context: ToolContext) -> dict:
    """Place a product order.

    Args:
        order: The order details including product, quantity, and address.
        tool_context: Injected by ADK — do not pass manually.

    Returns:
        A dict with 'order_id' str and 'status' str.
    """
    tool_context.state["last_order"] = order.model_dump()
    return {"order_id": "ORD-001", "status": "confirmed"}
```

---

## 5. FunctionTool with Confirmation

Wrap a function in `FunctionTool` with `require_confirmation=True` to pause
execution and request user approval before the tool runs.

```python
from google.adk.tools import FunctionTool

def delete_file(filename: str) -> dict:
    """Permanently delete a file.

    Args:
        filename: Path of the file to delete.

    Returns:
        A dict with 'deleted' bool and 'filename' str.
    """
    # implementation
    return {"deleted": True, "filename": filename}

dangerous_tool = FunctionTool(func=delete_file, require_confirmation=True)
```

Pass `dangerous_tool` (not the raw function) to `Agent(tools=[dangerous_tool])`.

---

## 6. Built-in Tools Reference Table

| Tool | Import | Purpose |
|------|--------|---------|
| `google_search` | `from google.adk.tools import google_search` | Web search via Google |
| `load_memory` | `from google.adk.tools import load_memory` | Load from memory service |
| `preload_memory` | `from google.adk.tools import preload_memory` | Preload memories into context |
| `exit_loop` | `from google.adk.tools import exit_loop` | Exit LoopAgent iteration |
| `transfer_to_agent` | `from google.adk.tools import transfer_to_agent` | Hand off to sub-agent |
| `get_user_choice` | `from google.adk.tools import get_user_choice` | Get user selection |
| `VertexAiSearchTool` | `from google.adk.tools import VertexAiSearchTool` | Enterprise search via Vertex AI |

---

## 7. McpToolset

`McpToolset` connects an ADK agent to any MCP server. Use `tool_filter` to expose
only specific tools. Always call `await runner.close()` when done — MCP sessions
hold open connections.

```python
from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    SseConnectionParams,
    StreamableHTTPConnectionParams,
)
from mcp import StdioServerParameters

# --- stdio (subprocess MCP server) ---
mcp_stdio = McpToolset(
    connection_params=StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    ),
    tool_filter=["read_file", "write_file"],
)

# --- stdio with explicit timeout ---
mcp_stdio_timeout = McpToolset(
    connection_params=StdioConnectionParams(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        timeout=30,
    ),
)

# --- SSE (Server-Sent Events) ---
mcp_sse = McpToolset(
    connection_params=SseConnectionParams(
        url="http://localhost:8080/sse",
        timeout=60,
    ),
)

# --- Streamable HTTP ---
mcp_http = McpToolset(
    connection_params=StreamableHTTPConnectionParams(
        url="http://localhost:8080/mcp",
        timeout=60,
    ),
    use_mcp_resources=True,
)

# Shutdown — always close after use
# await runner.close()
```
