from __future__ import annotations

import json
from typing import Any

import httpx
import pandas as pd
import structlog

from app.agent.connectors.base import BaseConnector
from app.core.config import settings

logger = structlog.get_logger()

_CORTEX_ANALYST_PATH = "/api/v2/cortex/analyst/message"


class SnowflakeConnector(BaseConnector):
    """Synchronous Snowflake connector.

    All public methods are synchronous and must be called via asyncio.to_thread()
    from the async tool layer.

    Cortex ANALYST requires Snowflake Enterprise tier or above.
    Cortex COMPLETE and SUMMARIZE require a supported warehouse.
    """

    def __init__(
        self,
        account: str | None = None,
        user: str | None = None,
        password: str | None = None,
        warehouse: str | None = None,
        database: str | None = None,
        schema: str | None = None,
        role: str | None = None,
    ) -> None:
        self._account = account or settings.SNOWFLAKE_ACCOUNT
        self._user = user or settings.SNOWFLAKE_USER
        self._password = password or settings.SNOWFLAKE_PASSWORD
        self._warehouse = warehouse or settings.SNOWFLAKE_WAREHOUSE
        self._database = database or settings.SNOWFLAKE_DATABASE
        self._schema = schema or settings.SNOWFLAKE_SCHEMA
        self._role = role or settings.SNOWFLAKE_ROLE

    def _connect(self) -> Any:
        import snowflake.connector

        kwargs: dict[str, Any] = {
            "account": self._account,
            "user": self._user,
            "password": self._password,
            "warehouse": self._warehouse,
            "database": self._database,
            "schema": self._schema,
        }
        if self._role:
            kwargs["role"] = self._role
        return snowflake.connector.connect(**kwargs)

    def execute_query(self, sql: str, **kwargs: object) -> pd.DataFrame:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            results = cursor.fetchmany(self.MAX_ROWS + 1)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            df = pd.DataFrame(results, columns=columns)
            df, _ = self._apply_row_limit(df)
            logger.info("snowflake_query_ok", rows=len(df), sql_preview=sql[:120])
            return df
        except Exception as exc:
            # Check for Enterprise-tier Cortex permission error
            err = str(exc)
            if "CORTEX" in err.upper() and "not enabled" in err.lower():
                raise RuntimeError(
                    "Snowflake Cortex requires Enterprise tier or above. "
                    "Use a direct SQL query instead."
                ) from exc
            logger.error("snowflake_query_error", error=err, sql_preview=sql[:120])
            raise
        finally:
            conn.close()

    def cortex_analyst(
        self, question: str, semantic_model_stage_path: str
    ) -> dict[str, Any]:
        """Call Snowflake Cortex ANALYST REST API.

        Returns dict with keys: sql (generated), explanation, raw_response.
        Two-step: (1) REST call to get SQL, (2) execute SQL to get DataFrame.

        Uses the connector session token for authentication.
        For production, replace with RSA key-pair JWT auth.
        """
        conn = self._connect()
        try:
            # Retrieve session token from the connection for REST API auth
            token = conn._rest.token  # noqa: SLF001 — private attr, replace with JWT in prod
            account_url = f"https://{self._account}.snowflakecomputing.com"

            payload = {
                "messages": [
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": question}],
                    }
                ],
                "semantic_model_file": semantic_model_stage_path,
            }

            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{account_url}{_CORTEX_ANALYST_PATH}",
                    headers={
                        "Authorization": f'Snowflake Token="{token}"',
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

            if response.status_code == 403:
                raise RuntimeError(
                    "Snowflake Cortex Analyst requires Enterprise tier or above."
                )
            response.raise_for_status()

            body = response.json()
            message = body.get("message", {})
            content = message.get("content", [])

            generated_sql = ""
            explanation = ""
            for item in content:
                if item.get("type") == "sql":
                    generated_sql = item.get("statement", "")
                elif item.get("type") == "text":
                    explanation = item.get("text", "")

            logger.info(
                "cortex_analyst_sql_generated",
                sql_preview=generated_sql[:120],
            )

            if not generated_sql:
                return {
                    "sql": "",
                    "explanation": explanation,
                    "df": pd.DataFrame(),
                    "error": "Cortex ANALYST did not return SQL.",
                }

            # Step 2: execute the generated SQL
            try:
                df = self.execute_query(generated_sql)
                return {"sql": generated_sql, "explanation": explanation, "df": df, "error": ""}
            except Exception as exec_exc:
                logger.error("cortex_analyst_exec_error", error=str(exec_exc), sql_preview=generated_sql[:120])
                return {
                    "sql": generated_sql,
                    "explanation": explanation,
                    "df": pd.DataFrame(),
                    "error": str(exec_exc),
                }
        finally:
            conn.close()

    def cortex_complete(self, prompt: str, model: str = "mistral-large2") -> str:
        """Run Snowflake Cortex COMPLETE SQL function."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT SNOWFLAKE.CORTEX.COMPLETE(%s, %s)",
                (model, prompt),
            )
            row = cursor.fetchone()
            result = row[0] if row else ""
            logger.info("cortex_complete_ok", model=model)
            return result
        except Exception as exc:
            err = str(exc)
            if "CORTEX" in err.upper() and "not enabled" in err.lower():
                raise RuntimeError(
                    "Snowflake Cortex requires Enterprise tier or above."
                ) from exc
            logger.error("cortex_complete_error", error=err)
            raise
        finally:
            conn.close()

    def cortex_summarize(self, text: str) -> str:
        """Run Snowflake Cortex SUMMARIZE SQL function."""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT SNOWFLAKE.CORTEX.SUMMARIZE(%s)", (text,))
            row = cursor.fetchone()
            result = row[0] if row else ""
            logger.info("cortex_summarize_ok", text_length=len(text))
            return result
        except Exception as exc:
            err = str(exc)
            if "CORTEX" in err.upper() and "not enabled" in err.lower():
                raise RuntimeError(
                    "Snowflake Cortex requires Enterprise tier or above."
                ) from exc
            logger.error("cortex_summarize_error", error=err)
            raise
        finally:
            conn.close()
