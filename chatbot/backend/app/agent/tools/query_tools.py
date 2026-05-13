from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pandas as pd
import structlog

from app.agent.connectors.bigquery_connector import BigQueryConnector
from app.agent.connectors.mssql_connector import MSSQLConnector
from app.agent.connectors.rest_connector import RestConnector
from app.agent.connectors.snowflake_connector import SnowflakeConnector
from app.core.config import settings

if TYPE_CHECKING:
    from app.agent.clarification_state import ClarificationState
    from app.agent.dataframe_store import DataFrameStore

logger = structlog.get_logger()


@dataclass
class AgentToolContext:
    """Injected into every tool call — carries session identity and shared stores."""

    user_id: str
    conversation_id: str
    store: "DataFrameStore"
    clarification_state: "ClarificationState"
    websocket: Any  # starlette WebSocket — for sending progress frames


def _make_summary(df: pd.DataFrame, label: str, truncated: bool) -> dict:
    return {
        "label": label,
        "rows": len(df),
        "columns": list(df.columns),
        "sample": df.head(3).to_dict(orient="records"),
        "truncated": truncated,
        "truncated_notice": (
            f"Result truncated to {settings.MAX_DATAFRAME_ROWS} rows." if truncated else ""
        ),
    }


# ── Snowflake ─────────────────────────────────────────────────────────────────

async def query_snowflake(
    sql: str,
    ctx: AgentToolContext,
    label: str = "snowflake_result",
    warehouse: str = "",
    database: str = "",
    schema: str = "",
) -> dict:
    """Execute SQL against Snowflake and store the result DataFrame.

    Returns a summary dict (row count, columns, 3-row sample) for the LLM.
    Full data is stored in DataFrameStore under `label` for response formatting.
    """
    connector = SnowflakeConnector(
        warehouse=warehouse or None,
        database=database or None,
        schema=schema or None,
    )
    df = await asyncio.to_thread(connector.execute_query, sql)
    truncated = len(df) >= settings.MAX_DATAFRAME_ROWS
    ctx.store.store(ctx.user_id, ctx.conversation_id, label, df)
    logger.info("query_snowflake_done", label=label, rows=len(df))
    return _make_summary(df, label, truncated)


async def cortex_analyst(
    question: str,
    ctx: AgentToolContext,
    semantic_model_stage_path: str = "",
    label: str = "cortex_analyst_result",
) -> dict:
    """Use Snowflake Cortex ANALYST to convert a natural language question to SQL
    and execute it. Returns generated SQL, explanation, and data summary.

    Requires Snowflake Enterprise tier or above.
    """
    connector = SnowflakeConnector()
    result = await asyncio.to_thread(
        connector.cortex_analyst, question, semantic_model_stage_path
    )

    if result.get("error"):
        logger.error("cortex_analyst_error", error=result["error"])
        return {
            "label": label,
            "sql": result.get("sql", ""),
            "explanation": result.get("explanation", ""),
            "error": result["error"],
            "rows": 0,
            "columns": [],
            "sample": [],
            "truncated": False,
        }

    df: pd.DataFrame = result["df"]
    truncated = len(df) >= settings.MAX_DATAFRAME_ROWS
    ctx.store.store(ctx.user_id, ctx.conversation_id, label, df)
    summary = _make_summary(df, label, truncated)
    summary["sql"] = result["sql"]
    summary["explanation"] = result["explanation"]
    return summary


async def cortex_complete(
    prompt: str,
    ctx: AgentToolContext,
    model: str = "mistral-large2",
) -> dict:
    """Run Snowflake Cortex COMPLETE on a prompt. Returns the generated text."""
    connector = SnowflakeConnector()
    text = await asyncio.to_thread(connector.cortex_complete, prompt, model)
    logger.info("cortex_complete_done", model=model)
    return {"result": text, "model": model}


async def cortex_summarize(
    text: str,
    ctx: AgentToolContext,
) -> dict:
    """Summarize a block of text using Snowflake Cortex SUMMARIZE."""
    connector = SnowflakeConnector()
    summary = await asyncio.to_thread(connector.cortex_summarize, text)
    logger.info("cortex_summarize_done", input_length=len(text))
    return {"summary": summary}


# ── BigQuery ──────────────────────────────────────────────────────────────────

async def query_bigquery(
    sql: str,
    ctx: AgentToolContext,
    label: str = "bigquery_result",
    project_id: str = "",
) -> dict:
    """Execute SQL against BigQuery (ADC auth) and store the result DataFrame."""
    connector = BigQueryConnector(project_id=project_id or None)
    df = await asyncio.to_thread(connector.execute_query, sql)
    truncated = len(df) >= settings.MAX_DATAFRAME_ROWS
    ctx.store.store(ctx.user_id, ctx.conversation_id, label, df)
    logger.info("query_bigquery_done", label=label, rows=len(df))
    return _make_summary(df, label, truncated)


# ── MSSQL ─────────────────────────────────────────────────────────────────────

async def query_mssql(
    sql: str,
    ctx: AgentToolContext,
    label: str = "mssql_result",
    server: str = "",
    database: str = "",
) -> dict:
    """Execute SQL against MSSQL (pyodbc) and store the result DataFrame."""
    connector = MSSQLConnector(
        server=server or None,
        database=database or None,
    )
    df = await asyncio.to_thread(connector.execute_query, sql)
    truncated = len(df) >= settings.MAX_DATAFRAME_ROWS
    ctx.store.store(ctx.user_id, ctx.conversation_id, label, df)
    logger.info("query_mssql_done", label=label, rows=len(df))
    return _make_summary(df, label, truncated)


# ── REST API ──────────────────────────────────────────────────────────────────

async def call_rest_api(
    prompt: str,
    ctx: AgentToolContext,
    url: str,
    method: str = "POST",
    headers: dict | None = None,
    label: str = "rest_result",
) -> dict:
    """POST the user's original prompt to a configured REST API and return the result.

    The prompt is sent as {"prompt": "<text>"} in the request body.
    The full API response is returned so the LLM can compose a natural language answer.
    """
    connector = RestConnector(url=url, method=method, headers=headers or {})
    result = await connector.call(prompt)
    logger.info("call_rest_api_done", label=label, status=result.get("status"))
    return {"label": label, "data": result["data"], "status": result["status"]}
