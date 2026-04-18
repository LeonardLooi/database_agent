from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationOut, ConversationWithMessages, MessageOut

logger = structlog.get_logger()
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def _get_user(token: str = Query(...)) -> str:
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    user_id: str = Depends(_get_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    """Return the most recent 100 conversations for the authenticated user.

    Args:
        user_id: Resolved from the bearer token via `_get_user`.
        db: Injected async database session.

    Returns:
        List of ConversationOut ordered by `updated_at` descending.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .limit(100)
    )
    return [ConversationOut.model_validate(c) for c in result.scalars().all()]


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: str,
    user_id: str = Depends(_get_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a conversation and all its messages.

    Args:
        conversation_id: UUID of the conversation to delete.
        user_id: Resolved from the bearer token — enforces ownership.
        db: Injected async database session.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
        HTTPException: 404 if the conversation does not exist or belongs to another user.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.delete(conv)
    await db.commit()


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
async def get_messages(
    conversation_id: str,
    user_id: str = Depends(_get_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    """Return all messages in a conversation, ordered chronologically.

    Args:
        conversation_id: UUID of the target conversation.
        user_id: Resolved from the bearer token — enforces ownership.
        db: Injected async database session.

    Returns:
        List of MessageOut ordered by `created_at` ascending.

    Raises:
        HTTPException: 401 if the token is missing or invalid.
        HTTPException: 404 if the conversation does not exist or belongs to another user.
    """
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    msgs_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return [MessageOut.model_validate(m) for m in msgs_result.scalars().all()]
