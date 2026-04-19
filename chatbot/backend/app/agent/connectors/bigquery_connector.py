from __future__ import annotations

import structlog

import pandas as pd

from app.agent.connectors.base import BaseConnector
from app.core.config import settings

logger = structlog.get_logger()


class BigQueryConnector(BaseConnector):
    """Synchronous BigQuery connector using Application Default Credentials.

    ADC resolution order (google.auth.default):
      1. GOOGLE_APPLICATION_CREDENTIALS env var → service account JSON file
      2. gcloud auth application-default login (mounted ~/.config/gcloud)
      3. Workload Identity (GKE / Cloud Run)
      4. Metadata server (GCE)

    In Docker Compose, set GOOGLE_APPLICATION_CREDENTIALS and volume-mount the
    service account JSON file into the container, e.g.:
      volumes:
        - ./sa-key.json:/secrets/sa-key.json
      environment:
        GOOGLE_APPLICATION_CREDENTIALS: /secrets/sa-key.json

    All public methods are synchronous — call via asyncio.to_thread().
    """

    def __init__(self, project_id: str | None = None) -> None:
        self._project_id = project_id or settings.BIGQUERY_PROJECT_ID

    def _client(self):
        from google.cloud import bigquery
        return bigquery.Client(project=self._project_id)

    def execute_query(self, sql: str, **kwargs: object) -> pd.DataFrame:
        client = self._client()
        try:
            query_job = client.query(sql)
            rows = query_job.result()
            df = rows.to_dataframe()
            df, _ = self._apply_row_limit(df)
            logger.info("bigquery_query_ok", rows=len(df), sql_preview=sql[:120])
            return df
        except Exception as exc:
            logger.error("bigquery_query_error", error=str(exc), sql_preview=sql[:120])
            raise
        finally:
            client.close()
