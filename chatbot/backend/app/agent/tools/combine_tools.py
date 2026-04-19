from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import pandas as pd
import structlog

from app.core.config import settings

if TYPE_CHECKING:
    from app.agent.dataframe_store import DataFrameStore

logger = structlog.get_logger()


def combine_dataframes(
    store: "DataFrameStore",
    user_id: str,
    conversation_id: str,
    label_a: str,
    label_b: str,
    join_key: str = "",
    how: Literal["inner", "left", "right", "outer"] = "inner",
    result_label: str = "combined_result",
) -> dict:
    """Merge two DataFrames from the store into a new combined result.

    Edge cases handled:
    - Missing label: returns descriptive error
    - Empty DataFrame on either side: returns empty combined with notice
    - Column name mismatch on join_key: returns descriptive error
    - Type mismatch on join_key: coerces to string before merge with warning
    - Result exceeds MAX_ROWS: truncated to MAX_ROWS

    Returns summary dict. Full merged DataFrame stored under `result_label`.
    """
    df_a = store.retrieve(user_id, conversation_id, label_a)
    df_b = store.retrieve(user_id, conversation_id, label_b)

    if df_a is None:
        return {"error": f"Dataset '{label_a}' not found in session. Run the query first."}
    if df_b is None:
        return {"error": f"Dataset '{label_b}' not found in session. Run the query first."}

    if df_a.empty:
        return {"error": f"Dataset '{label_a}' returned 0 rows — nothing to combine."}
    if df_b.empty:
        return {"error": f"Dataset '{label_b}' returned 0 rows — nothing to combine."}

    if join_key and join_key not in df_a.columns:
        cols_a = list(df_a.columns)
        return {
            "error": (
                f"Join key '{join_key}' not found in '{label_a}'. "
                f"Available columns: {cols_a}"
            )
        }
    if join_key and join_key not in df_b.columns:
        cols_b = list(df_b.columns)
        return {
            "error": (
                f"Join key '{join_key}' not found in '{label_b}'. "
                f"Available columns: {cols_b}"
            )
        }

    type_warning = ""
    if join_key:
        type_a = df_a[join_key].dtype
        type_b = df_b[join_key].dtype
        if type_a != type_b:
            df_a = df_a.copy()
            df_b = df_b.copy()
            df_a[join_key] = df_a[join_key].astype(str)
            df_b[join_key] = df_b[join_key].astype(str)
            type_warning = (
                f"Join key '{join_key}' type mismatch ({type_a} vs {type_b}). "
                "Coerced both to string for merge."
            )
            logger.warning("combine_type_coercion", key=join_key, type_a=str(type_a), type_b=str(type_b))

    python_code = (
        f"import pandas as pd\n"
        f"combined = pd.merge(df_{label_a}, df_{label_b}, on='{join_key}', how='{how}')"
    )

    try:
        if join_key:
            merged = pd.merge(df_a, df_b, on=join_key, how=how)
        else:
            # No join key — concatenate side by side
            merged = pd.concat([df_a.reset_index(drop=True), df_b.reset_index(drop=True)], axis=1)
            python_code = (
                f"import pandas as pd\n"
                f"combined = pd.concat([df_{label_a}, df_{label_b}], axis=1)"
            )
    except Exception as exc:
        logger.error("combine_merge_error", error=str(exc))
        return {"error": f"Merge failed: {exc}"}

    truncated = len(merged) > settings.MAX_DATAFRAME_ROWS
    if truncated:
        merged = merged.iloc[: settings.MAX_DATAFRAME_ROWS].copy()

    store.store(user_id, conversation_id, result_label, merged)
    logger.info("combine_done", result_label=result_label, rows=len(merged))

    return {
        "label": result_label,
        "rows": len(merged),
        "columns": list(merged.columns),
        "sample": merged.head(3).to_dict(orient="records"),
        "truncated": truncated,
        "type_warning": type_warning,
        "python_code": python_code,
    }
