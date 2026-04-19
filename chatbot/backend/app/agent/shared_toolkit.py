from __future__ import annotations

from typing import Any

import structlog

from app.agent.intent_loader import YAMLIntentLoader
from app.agent.tools.clarification_tools import ask_clarification
from app.agent.tools.combine_tools import combine_dataframes
from app.agent.tools.query_tools import (
    AgentToolContext,
    cortex_analyst,
    cortex_complete,
    cortex_summarize,
    query_bigquery,
    query_mssql,
    query_snowflake,
)
from app.core.config import settings

logger = structlog.get_logger()


class SharedToolkit:
    """Singleton holding the canonical tool definitions for all providers.

    Canonical tools are plain async Python functions (query_tools.py).
    This class adapts them to each provider's registration format:
      - Anthropic  : tool_use schema dicts
      - OpenAI     : function_calling schema dicts
      - ADK        : list of async functions (wrapped by ADK FunctionTool)
      - Strands    : list of async functions (decorated at registration time)

    Usage:
        toolkit = SharedToolkit()
        anthropic_tools = toolkit.get_anthropic_tools()
        openai_tools    = toolkit.get_openai_tools()
        adk_tools       = toolkit.get_adk_functions()   # raw callables for ADK
    """

    _instance: SharedToolkit | None = None

    def __new__(cls) -> SharedToolkit:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self.intent_loader = YAMLIntentLoader(settings.INTENT_DIR)
        self._initialized = True
        logger.info("shared_toolkit_ready", intents=self.intent_loader.all_names())

    # ── canonical tool metadata ───────────────────────────────────────────────

    _TOOL_SCHEMAS: list[dict] = [
        {
            "name": "query_snowflake",
            "description": "Execute a SQL query against Snowflake and return results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "label": {"type": "string", "description": "Result label for DataFrameStore (default: snowflake_result)"},
                    "warehouse": {"type": "string", "description": "Snowflake warehouse override"},
                    "database": {"type": "string", "description": "Snowflake database override"},
                    "schema": {"type": "string", "description": "Snowflake schema override"},
                },
                "required": ["sql"],
            },
        },
        {
            "name": "cortex_analyst",
            "description": "Use Snowflake Cortex ANALYST to convert a natural language question to SQL and execute it. Requires Enterprise tier.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Natural language question about Snowflake data"},
                    "semantic_model_stage_path": {"type": "string", "description": "Stage path to the semantic model YAML (e.g. @stage/model.yaml)"},
                    "label": {"type": "string", "description": "Result label for DataFrameStore"},
                },
                "required": ["question"],
            },
        },
        {
            "name": "cortex_complete",
            "description": "Run Snowflake Cortex COMPLETE on a prompt to generate text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Prompt text for Cortex COMPLETE"},
                    "model": {"type": "string", "description": "Cortex model name (default: mistral-large2)"},
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "cortex_summarize",
            "description": "Summarize a block of text using Snowflake Cortex SUMMARIZE.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to summarize"},
                },
                "required": ["text"],
            },
        },
        {
            "name": "query_bigquery",
            "description": "Execute a SQL query against BigQuery and return results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "label": {"type": "string", "description": "Result label for DataFrameStore (default: bigquery_result)"},
                    "project_id": {"type": "string", "description": "GCP project ID override"},
                },
                "required": ["sql"],
            },
        },
        {
            "name": "query_mssql",
            "description": "Execute a SQL query against MSSQL (SQL Server) and return results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "label": {"type": "string", "description": "Result label for DataFrameStore (default: mssql_result)"},
                    "server": {"type": "string", "description": "MSSQL server override"},
                    "database": {"type": "string", "description": "MSSQL database override"},
                },
                "required": ["sql"],
            },
        },
        {
            "name": "combine_dataframes",
            "description": "Merge two previously retrieved DataFrames into a combined result using a join key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label_a": {"type": "string", "description": "Label of the first DataFrame in the session store"},
                    "label_b": {"type": "string", "description": "Label of the second DataFrame in the session store"},
                    "join_key": {"type": "string", "description": "Column name to join on (empty = concatenate side by side)"},
                    "how": {"type": "string", "enum": ["inner", "left", "right", "outer"], "description": "Join type"},
                    "result_label": {"type": "string", "description": "Label for the combined result"},
                },
                "required": ["label_a", "label_b"],
            },
        },
        {
            "name": "ask_clarification",
            "description": "Ask the user a clarifying question when the intent is ambiguous. Use this before executing any query when confidence is low.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Clarifying question to ask the user"},
                    "candidates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of intent candidates to present as options",
                    },
                },
                "required": ["message"],
            },
        },
    ]

    # ── provider-specific formats ─────────────────────────────────────────────

    def get_anthropic_tools(self) -> list[dict]:
        """Anthropic tool_use format."""
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"],
            }
            for t in self._TOOL_SCHEMAS
        ]

    def get_openai_tools(self) -> list[dict]:
        """OpenAI function_calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["parameters"],
                },
            }
            for t in self._TOOL_SCHEMAS
        ]

    def get_adk_functions(self) -> list[Any]:
        """Raw async callables for ADK FunctionTool registration."""
        return [
            query_snowflake,
            cortex_analyst,
            cortex_complete,
            cortex_summarize,
            query_bigquery,
            query_mssql,
        ]

    def get_strands_tools(self) -> list[Any]:
        """Async callables for Strands Agent tool registration."""
        return [
            query_snowflake,
            cortex_analyst,
            cortex_complete,
            cortex_summarize,
            query_bigquery,
            query_mssql,
            ask_clarification,
        ]

    def dispatch(self, tool_name: str, args: dict, ctx: AgentToolContext) -> Any:
        """Dispatch a tool call by name. Returns a coroutine for await."""
        dispatch_map = {
            "query_snowflake": lambda: query_snowflake(ctx=ctx, **args),
            "cortex_analyst": lambda: cortex_analyst(ctx=ctx, **args),
            "cortex_complete": lambda: cortex_complete(ctx=ctx, **args),
            "cortex_summarize": lambda: cortex_summarize(ctx=ctx, **args),
            "query_bigquery": lambda: query_bigquery(ctx=ctx, **args),
            "query_mssql": lambda: query_mssql(ctx=ctx, **args),
            "combine_dataframes": lambda: _dispatch_combine(args, ctx),
            "ask_clarification": lambda: ask_clarification(ctx=ctx, **args),
        }
        fn = dispatch_map.get(tool_name)
        if fn is None:
            raise ValueError(f"Unknown tool: '{tool_name}'")
        return fn()

    def intents_as_system_context(self) -> str:
        """Render all YAML intents as a system prompt block for provider LLMs."""
        lines = [
            "You are a data assistant. Available data intents:\n",
        ]
        for intent in self.intent_loader.all_intents():
            connectors = ", ".join(c.type for c in intent.connectors)
            lines.append(f"- **{intent.name}**: {intent.description} (connectors: {connectors})")
            if intent.keywords:
                lines.append(f"  Keywords: {', '.join(intent.keywords)}")
        lines.append(
            "\nWhen the user asks a data question, select the best matching intent and "
            "call the appropriate tool. If intent confidence is low, call ask_clarification "
            "BEFORE running any query. For multi-source queries, fetch each source separately "
            "then call combine_dataframes."
        )
        return "\n".join(lines)


def _dispatch_combine(args: dict, ctx: AgentToolContext) -> Any:
    import asyncio

    async def _run():
        return await asyncio.to_thread(
            combine_dataframes,
            store=ctx.store,
            user_id=ctx.user_id,
            conversation_id=ctx.conversation_id,
            **args,
        )

    return _run()
