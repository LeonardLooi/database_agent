"""Tests for database connectors — BaseConnector, BigQuery, MSSQL with mocks."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from app.agent.connectors.base import BaseConnector
from app.agent.connectors.bigquery_connector import BigQueryConnector
from app.agent.connectors.mssql_connector import MSSQLConnector


# ── BaseConnector ─────────────────────────────────────────────────────────────

class _ConcreteConnector(BaseConnector):
    def execute_query(self, sql: str, **kwargs: object) -> pd.DataFrame:
        return pd.DataFrame({"col": range(5)})


class TestBaseConnector:
    def test_apply_row_limit_no_truncation(self):
        conn = _ConcreteConnector()
        df = pd.DataFrame({"x": range(100)})
        result, truncated = conn._apply_row_limit(df)
        assert truncated is False
        assert len(result) == 100

    def test_apply_row_limit_truncates_at_max(self):
        conn = _ConcreteConnector()
        big_df = pd.DataFrame({"x": range(conn.MAX_ROWS + 10)})
        result, truncated = conn._apply_row_limit(big_df)
        assert truncated is True
        assert len(result) == conn.MAX_ROWS

    def test_execute_query_concrete(self):
        conn = _ConcreteConnector()
        df = conn.execute_query("SELECT 1")
        assert len(df) == 5


# ── BigQueryConnector ─────────────────────────────────────────────────────────

class TestBigQueryConnector:
    def test_init_uses_project_id_from_settings(self):
        conn = BigQueryConnector()
        from app.core.config import settings
        assert conn._project_id == settings.BIGQUERY_PROJECT_ID

    def test_init_with_explicit_project_id(self):
        conn = BigQueryConnector(project_id="my-project")
        assert conn._project_id == "my-project"

    def test_execute_query_success(self):
        expected_df = pd.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})

        mock_rows = MagicMock()
        mock_rows.to_dataframe.return_value = expected_df
        mock_job = MagicMock()
        mock_job.result.return_value = mock_rows
        mock_client = MagicMock()
        mock_client.query.return_value = mock_job

        with patch.object(BigQueryConnector, "_client", return_value=mock_client):
            conn = BigQueryConnector(project_id="test")
            df = conn.execute_query("SELECT name, score FROM table")

        assert list(df.columns) == ["name", "score"]
        assert len(df) == 2
        mock_client.close.assert_called_once()

    def test_execute_query_error_raises(self):
        mock_client = MagicMock()
        mock_client.query.side_effect = RuntimeError("BQ connection failed")

        with patch.object(BigQueryConnector, "_client", return_value=mock_client):
            conn = BigQueryConnector(project_id="test")
            with pytest.raises(RuntimeError, match="BQ connection failed"):
                conn.execute_query("SELECT 1")

        mock_client.close.assert_called_once()

    def test_execute_query_truncates_large_result(self):
        large_df = pd.DataFrame({"x": range(BigQueryConnector.MAX_ROWS + 50)})

        mock_rows = MagicMock()
        mock_rows.to_dataframe.return_value = large_df
        mock_job = MagicMock()
        mock_job.result.return_value = mock_rows
        mock_client = MagicMock()
        mock_client.query.return_value = mock_job

        with patch.object(BigQueryConnector, "_client", return_value=mock_client):
            conn = BigQueryConnector(project_id="test")
            df = conn.execute_query("SELECT x FROM big_table")

        assert len(df) == BigQueryConnector.MAX_ROWS


# ── MSSQLConnector ────────────────────────────────────────────────────────────

class TestMSSQLConnector:
    def test_init_uses_settings_defaults(self):
        conn = MSSQLConnector()
        from app.core.config import settings
        assert conn._server == settings.MSSQL_SERVER
        assert conn._database == settings.MSSQL_DATABASE

    def test_init_with_explicit_params(self):
        conn = MSSQLConnector(server="myserver", database="mydb")
        assert conn._server == "myserver"
        assert conn._database == "mydb"

    def test_connection_string_format(self):
        conn = MSSQLConnector(server="srv", database="db", username="u", password="p")
        cs = conn._connection_string()
        assert "SERVER=srv" in cs
        assert "DATABASE=db" in cs
        assert "UID=u" in cs
        assert "PWD=p" in cs
        assert "TrustServerCertificate=yes" in cs

    def test_execute_query_success(self):
        mock_cursor = MagicMock()
        mock_cursor.description = [("col1",), ("col2",)]
        mock_cursor.fetchmany.return_value = [("a", 1), ("b", 2)]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc = MagicMock()
        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            conn = MSSQLConnector(server="s", database="d", username="u", password="p")
            df = conn.execute_query("SELECT col1, col2 FROM t")

        assert list(df.columns) == ["col1", "col2"]
        assert len(df) == 2
        mock_conn.close.assert_called_once()

    def test_execute_query_error_raises(self):
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",)]
        mock_cursor.execute.side_effect = RuntimeError("MSSQL connection failed")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc = MagicMock()
        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            conn = MSSQLConnector(server="s", database="d", username="u", password="p")
            with pytest.raises(RuntimeError):
                conn.execute_query("SELECT 1")

        mock_conn.close.assert_called_once()

    def test_execute_query_no_columns(self):
        mock_cursor = MagicMock()
        mock_cursor.description = None
        mock_cursor.fetchmany.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_pyodbc = MagicMock()
        mock_pyodbc.connect.return_value = mock_conn

        with patch.dict("sys.modules", {"pyodbc": mock_pyodbc}):
            conn = MSSQLConnector()
            df = conn.execute_query("EXEC some_proc")

        assert list(df.columns) == []
