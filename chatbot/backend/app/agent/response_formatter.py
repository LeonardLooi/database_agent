from __future__ import annotations

import io

import structlog

from app.agent.dataframe_store import DataFrameStore
from app.schemas.ws_messages import WsAgentResponse
from app.services.llm.base import AgentLoopResult

logger = structlog.get_logger()


class ResponseFormatter:
    """Build a WsAgentResponse from an AgentLoopResult and DataFrameStore."""

    def __init__(self, store: DataFrameStore) -> None:
        self._store = store

    def build(
        self,
        result: AgentLoopResult,
        conversation_id: str,
        user_id: str,
        provider: str,
        model: str,
    ) -> WsAgentResponse:
        table_md = ""
        csv_data = ""
        row_count = result.row_count
        truncated = result.truncated

        # Find the last stored DataFrame for this conversation
        labels = self._store.list_labels(user_id, conversation_id)
        target_label = result.final_label or (labels[-1] if labels else "")

        if target_label:
            df = self._store.retrieve(user_id, conversation_id, target_label)
            if df is not None and not df.empty:
                row_count = len(df)
                # CSV
                buf = io.StringIO()
                df.to_csv(buf, index=False)
                csv_data = buf.getvalue()
                # Markdown table (cap at 50 rows in the chat display)
                display_df = df.head(50)
                table_md = _df_to_markdown(display_df)
                truncated = result.truncated or (row_count > 50)

        return WsAgentResponse(
            conversation_id=conversation_id,
            explanation=result.explanation,
            table_md=table_md,
            csv=csv_data,
            sql_used=result.sql_used,
            python_used=result.python_used,
            truncated=truncated,
            row_count=row_count,
            provider=provider,
            model=model,
        )


def _df_to_markdown(df) -> str:  # type: ignore[no-untyped-def]
    """Convert a pandas DataFrame to a GitHub-flavoured markdown table."""
    if df.empty:
        return ""
    cols = list(df.columns)
    header = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = []
    for _, row in df.iterrows():
        cells = " | ".join(str(v).replace("|", "\\|") for v in row)
        rows.append(f"| {cells} |")
    return "\n".join([header, sep] + rows)
