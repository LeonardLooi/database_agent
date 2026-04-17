# Agentic AI Tool Patterns

Patterns for defining, validating, and managing tools in LangGraph agents.

## Basic @tool Pattern

**File:** `src/<service>/agents/tools/search.py`

```python
from __future__ import annotations

import json

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ...core.logging import get_logger

logger = get_logger(__name__)


@tool
def search_web(query: str) -> str:
    """Search the web for current information.

    Args:
        query: The search query string. Be specific for better results.

    Returns:
        JSON string of search results with title, url, and snippet.
    """
    try:
        # Replace with actual search API call
        results = _call_search_api(query)
        logger.info("tool_search_web", query=query, result_count=len(results))
        return json.dumps(results)
    except Exception as e:
        logger.error("tool_search_web_failed", query=query, error=str(e))
        return f"Search failed: {e}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression safely.

    Args:
        expression: A mathematical expression (e.g., '2 + 2', 'sqrt(16)').

    Returns:
        The result as a string.
    """
    try:
        # Use ast.literal_eval or a safe math parser — never eval()
        import ast
        result = ast.literal_eval(expression)
        return str(result)
    except (ValueError, SyntaxError) as e:
        logger.error("tool_calculator_failed", expression=expression, error=str(e))
        return f"Invalid expression: {e}"
```

## Pydantic-Validated Tool Inputs

For complex tool inputs, use Pydantic models for validation.

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field


class DatabaseQueryInput(BaseModel):
    """Input schema for database query tool."""

    table: str = Field(..., description="Table name to query")
    filters: dict[str, str] = Field(default_factory=dict, description="Column-value filter pairs")
    limit: int = Field(default=10, ge=1, le=100, description="Max rows to return")
    columns: list[str] = Field(default_factory=list, description="Columns to select (empty = all)")


@tool(args_schema=DatabaseQueryInput)
def query_database(table: str, filters: dict[str, str], limit: int = 10, columns: list[str] | None = None) -> str:
    """Query the database with filters and return matching rows.

    Use this tool when you need to look up structured data.
    Always specify filters to avoid returning too many rows.
    """
    try:
        # Build and execute query safely (parameterized)
        query = build_safe_query(table, filters, limit, columns or [])
        results = execute_query(query)
        logger.info("tool_query_database", table=table, result_count=len(results))
        return json.dumps(results, default=str)
    except Exception as e:
        logger.error("tool_query_database_failed", table=table, error=str(e))
        return f"Database query failed: {e}"
```

## API Integration Tool

```python
import httpx
from langchain_core.tools import tool


@tool
async def call_external_api(endpoint: str, method: str = "GET", payload: str = "") -> str:
    """Call an external API endpoint.

    Args:
        endpoint: The API endpoint path (e.g., '/users/123').
        method: HTTP method — GET or POST only.
        payload: JSON string payload for POST requests.

    Returns:
        JSON string of the API response.
    """
    if method not in ("GET", "POST"):
        return "Error: Only GET and POST methods are allowed"

    base_url = settings.external_api_base_url
    url = f"{base_url}{endpoint}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url)
            else:
                response = await client.post(url, json=json.loads(payload) if payload else {})

            response.raise_for_status()
            logger.info("tool_api_call", endpoint=endpoint, status=response.status_code)
            return response.text

    except httpx.TimeoutException:
        logger.error("tool_api_timeout", endpoint=endpoint)
        return f"API call timed out after 30s: {endpoint}"
    except httpx.HTTPStatusError as e:
        logger.error("tool_api_error", endpoint=endpoint, status=e.response.status_code)
        return f"API returned error {e.response.status_code}: {e.response.text[:200]}"
    except Exception as e:
        logger.error("tool_api_failed", endpoint=endpoint, error=str(e))
        return f"API call failed: {e}"
```

## MCP Server Building

Build a Model Context Protocol server in Python using the `mcp` SDK.

**File:** `src/<service>/mcp_server.py`

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server = Server("my-agent-tools")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for MCP clients."""
    return [
        Tool(
            name="search_knowledge_base",
            description="Search the internal knowledge base for relevant documents",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute a tool by name."""
    if name == "search_knowledge_base":
        results = await search_kb(arguments["query"], arguments.get("max_results", 5))
        return [TextContent(type="text", text=json.dumps(results))]

    raise ValueError(f"Unknown tool: {name}")


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
```

## MCP Client Consumption in LangGraph

```python
from langchain_core.tools import tool


def create_mcp_tools(mcp_client) -> list:
    """Wrap MCP server tools as LangChain tools for use in graphs."""

    @tool
    async def mcp_search(query: str) -> str:
        """Search via MCP server."""
        result = await mcp_client.call_tool("search_knowledge_base", {"query": query})
        return result[0].text

    return [mcp_search]
```

## Tool Retry and Timeout Patterns

```python
import asyncio
from functools import wraps


def with_retry(max_retries: int = 3, delay: float = 1.0):
    """Decorator to add retry logic to async tools."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "tool_retry",
                        tool=func.__name__,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(delay * (2 ** attempt))  # Exponential backoff
            return f"Tool failed after {max_retries} retries: {last_error}"
        return wrapper
    return decorator


def with_timeout(seconds: float = 30.0):
    """Decorator to add timeout to async tools."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error("tool_timeout", tool=func.__name__, timeout=seconds)
                return f"Tool timed out after {seconds}s"
        return wrapper
    return decorator


# Usage
@tool
@with_retry(max_retries=3)
@with_timeout(seconds=30.0)
async def resilient_search(query: str) -> str:
    """Search with automatic retry and timeout."""
    # Implementation
    ...
```

## Tool Registration Pattern

Centralize tool registration for maintainability.

**File:** `src/<service>/agents/tools/__init__.py`

```python
from .api_tools import call_external_api
from .db_tools import query_database
from .search_tools import search_web

# All tools available for agent binding
ALL_TOOLS = [
    search_web,
    query_database,
    call_external_api,
]

# Tool subsets for different agent types
RESEARCH_TOOLS = [search_web]
DATA_TOOLS = [query_database]
INTEGRATION_TOOLS = [call_external_api]
```

## Key Rules

| Rule | Standard |
|------|----------|
| Docstrings | Every `@tool` MUST have a descriptive docstring — LLMs read these to decide when to use tools |
| Error handling | Every tool MUST have try/except — return error string, never raise |
| Return type | Always return `str` — LLMs consume text |
| Logging | Log every tool invocation and error with context |
| Validation | Use `args_schema` for complex inputs |
| Side effects | Tools that modify data MUST require HITL approval |
| Timeouts | All I/O tools MUST have timeouts |
| Security | Never pass raw user input to shell commands or SQL |
