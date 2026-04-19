from __future__ import annotations

import structlog
import pandas as pd

from app.agent.connectors.base import BaseConnector
from app.core.config import settings

logger = structlog.get_logger()


class MSSQLConnector(BaseConnector):
    """Synchronous MSSQL connector using pyodbc.

    Requires Microsoft ODBC Driver 18 for SQL Server to be installed.
    The Dockerfile installs it before pip install.

    All public methods are synchronous — call via asyncio.to_thread().
    """

    def __init__(
        self,
        server: str | None = None,
        database: str | None = None,
        username: str | None = None,
        password: str | None = None,
        driver: str | None = None,
    ) -> None:
        self._server = server or settings.MSSQL_SERVER
        self._database = database or settings.MSSQL_DATABASE
        self._username = username or settings.MSSQL_USERNAME
        self._password = password or settings.MSSQL_PASSWORD
        self._driver = driver or settings.MSSQL_DRIVER

    def _connection_string(self) -> str:
        return (
            f"DRIVER={{{self._driver}}};"
            f"SERVER={self._server};"
            f"DATABASE={self._database};"
            f"UID={self._username};"
            f"PWD={self._password};"
            "TrustServerCertificate=yes;"
            "Encrypt=yes;"
        )

    def execute_query(self, sql: str, **kwargs: object) -> pd.DataFrame:
        import pyodbc

        conn = pyodbc.connect(self._connection_string())
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(self.MAX_ROWS + 1)
            df = pd.DataFrame.from_records(rows, columns=columns)
            df, _ = self._apply_row_limit(df)
            logger.info("mssql_query_ok", rows=len(df), sql_preview=sql[:120])
            return df
        except Exception as exc:
            logger.error("mssql_query_error", error=str(exc), sql_preview=sql[:120])
            raise
        finally:
            conn.close()
