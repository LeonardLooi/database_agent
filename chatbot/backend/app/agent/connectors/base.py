from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class BaseConnector(ABC):
    """Abstract base for all database connectors.

    All execute_* methods must be implemented as synchronous operations and
    called via asyncio.to_thread() in the async tool layer — never called
    directly in an async context as they block the event loop.
    """

    MAX_ROWS: int = 10_000

    @abstractmethod
    def execute_query(self, sql: str, **kwargs: object) -> pd.DataFrame:
        """Execute a SQL query and return a DataFrame, capped at MAX_ROWS."""

    def _apply_row_limit(self, df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
        """Return (df, truncated). Truncates to MAX_ROWS if needed."""
        if len(df) > self.MAX_ROWS:
            return df.iloc[: self.MAX_ROWS].copy(), True
        return df, False
