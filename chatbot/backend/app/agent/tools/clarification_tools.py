from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from app.agent.tools.query_tools import AgentToolContext

logger = structlog.get_logger()


async def ask_clarification(
    message: str,
    ctx: "AgentToolContext",
    candidates: list[str] | None = None,
) -> dict:
    """Pause the agent loop and ask the user a clarifying question.

    Writes pending state to Redis so the next incoming WS message for this
    session is routed back to the waiting loop instead of treated as a new turn.

    Sends a WsClarificationRequest frame to the WebSocket client.
    """
    from app.schemas.ws_messages import WsClarificationRequest

    candidates = candidates or []

    ctx.clarification_state.set_pending(
        user_id=ctx.user_id,
        conversation_id=ctx.conversation_id,
        question=message,
        candidates=candidates,
        original_query="",
    )

    frame = WsClarificationRequest(message=message, candidates=candidates)
    await ctx.websocket.send_text(frame.model_dump_json())

    logger.info(
        "clarification_sent",
        user_id=ctx.user_id,
        conversation_id=ctx.conversation_id,
        candidates=candidates,
    )

    return {
        "status": "clarification_sent",
        "message": message,
        "candidates": candidates,
    }
