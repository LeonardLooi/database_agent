from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.conversation import Conversation, Message
from app.schemas.ws_messages import MsgIn, WsIncoming
from app.services.llm.factory import LLMProviderFactory
from app.services.llm_service import LLMService

logger = structlog.get_logger()
router = APIRouter(tags=["websocket"])


async def _get_or_create_conversation(
    db: AsyncSession,
    conversation_id: str,
    user_id: str,
) -> tuple[Conversation, bool]:
    """Returns (conversation, is_new). is_new=True when just created."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        conv = Conversation(id=conversation_id, user_id=user_id)
        db.add(conv)
        await db.flush()
        return conv, True
    return conv, False


async def _save_messages(
    db: AsyncSession,
    conversation_id: str,
    user_content: str,
    assistant_content: str,
    provider: str,
    model: str,
    token_count: int,
) -> None:
    db.add(Message(conversation_id=conversation_id, role="user", content=user_content))
    db.add(
        Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            provider=provider,
            model=model,
            token_count=token_count,
        )
    )
    await db.commit()


async def _generate_and_send_title(
    websocket: WebSocket,
    llm_service: LLMService,
    content: str,
    conversation_id: str,
) -> None:
    title = await llm_service.generate_title(content)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.title = title
            await db.commit()
    try:
        await manager.send_json(
            {"type": "title", "conversation_id": conversation_id, "title": title},
            websocket,
        )
    except Exception:
        pass  # client disconnected before title was ready — silently drop


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """Handle a persistent WebSocket connection for streaming chat.

    On connect, immediately sends an `{"type": "providers", ...}` frame listing
    all registered LLM providers and their available models.

    Message flow per user turn:
      1. Client sends `{"type": "message", ...}` with `messages` and optional `model`.
      2. Server streams `{"type": "delta", "content": "<token>"}` frames.
      3. Server sends `{"type": "done", "conversation_id": ..., "token_count": ...}`.
      4. For new conversations, a `{"type": "title", ...}` frame follows asynchronously.

    Args:
        websocket: The active WebSocket connection.
        token: JWT bearer token passed as a query parameter.

    Raises:
        Closes with code 4001 if the token is missing or invalid.
    """
    user_id = decode_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(websocket, user_id)

    # Send available providers immediately on connect
    providers_data = LLMProviderFactory.get_providers_data()
    await manager.send_json({"type": "providers", "data": providers_data}, websocket)

    try:
        while True:
            raw = await websocket.receive_json()
            incoming = WsIncoming.model_validate(raw)

            if incoming.type == "ping":
                await manager.send_json({"type": "pong"}, websocket)
                continue

            # ── resolve provider and model ──────────────────────────────────
            _registered = LLMProviderFactory.available_providers()
            active_provider_name = settings.LLM_PROVIDER if settings.LLM_PROVIDER in _registered else (
                _registered[0] if _registered else "anthropic"
            )

            provider = None
            resolved_model = incoming.model or ""

            if incoming.model:
                mapped = LLMProviderFactory.resolve_provider_for_model(incoming.model)
                target_provider_name = mapped or active_provider_name
                try:
                    provider = LLMProviderFactory.create(target_provider_name)
                    resolved_model = incoming.model
                except Exception as exc:
                    logger.warning("provider_switch_failed", error=str(exc))

            if provider is None:
                try:
                    provider = LLMProviderFactory.create()
                except Exception as exc:
                    await manager.send_json(
                        {"type": "error", "message": str(exc), "code": 500},
                        websocket,
                    )
                    continue

            if not resolved_model:
                resolved_model = provider.default_model

            llm_service = LLMService(provider=provider)

            # ── get or create conversation ───────────────────────────────────
            conv_id = incoming.conversation_id or str(uuid.uuid4())

            # ── stream response ──────────────────────────────────────────────
            full_content = ""
            try:
                async for token in llm_service.stream(
                    incoming.messages,
                    resolved_model,
                    incoming.temperature,
                ):
                    full_content += token
                    await manager.send_json({"type": "delta", "content": token}, websocket)

            except Exception as exc:
                logger.error("llm_stream_failed", error=str(exc), user_id=user_id)
                await manager.send_json(
                    {"type": "error", "message": "LLM error — check server logs", "code": 500},
                    websocket,
                )
                continue

            token_count = max(1, len(full_content) // 4)

            # ── persist to DB before notifying client ────────────────────────
            user_content = incoming.messages[-1].content if incoming.messages else ""
            async with AsyncSessionLocal() as db:
                _, is_new_conversation = await _get_or_create_conversation(db, conv_id, user_id)
                await _save_messages(
                    db,
                    conv_id,
                    user_content,
                    full_content,
                    provider.provider_name,
                    resolved_model,
                    token_count,
                )

            await manager.send_json(
                {
                    "type": "done",
                    "conversation_id": conv_id,
                    "token_count": token_count,
                    "provider": provider.provider_name,
                    "model": resolved_model,
                },
                websocket,
            )

            # ── generate title on first message (background) ─────────────────
            if is_new_conversation and user_content:
                asyncio.create_task(
                    _generate_and_send_title(
                        websocket,
                        llm_service,
                        user_content,
                        conv_id,
                    )
                )

    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", user_id=user_id)
    except Exception as exc:
        logger.error("ws_unexpected_error", user_id=user_id, error=str(exc))
    finally:
        manager.disconnect(websocket, user_id)
