from __future__ import annotations

import asyncio
import uuid

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.clarification_state import ClarificationState
from app.agent.dataframe_store import DataFrameStore
from app.agent.orchestrator import ChatOrchestrator
from app.agent.response_formatter import ResponseFormatter
from app.agent.session_model_store import SessionModelStore
from app.agent.skill_registry import SkillRegistry
from app.agent.tools.query_tools import AgentToolContext
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import decode_token
from app.core.ws_manager import manager
from app.models.conversation import Conversation, Message
from app.schemas.ws_messages import MsgIn, WsIncoming
from app.services.llm.base import RoutingDecision
from app.services.llm.factory import LLMProviderFactory
from app.services.llm_service import LLMService

logger = structlog.get_logger()
router = APIRouter(tags=["websocket"])

# Lazily initialized shared objects (created once per worker process)
_redis_client = None
_skill_registry: SkillRegistry | None = None
_session_model_store: SessionModelStore | None = None


def _get_redis():
    global _redis_client
    if not settings.REDIS_ENABLED:
        return None
    if _redis_client is None:
        import redis as redis_lib

        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def _get_skill_registry() -> SkillRegistry:
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry(settings.SKILLS_DIR)
    return _skill_registry


def _get_session_model_store() -> SessionModelStore:
    global _session_model_store
    if _session_model_store is None:
        _session_model_store = SessionModelStore(_get_redis())
    return _session_model_store


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
            active_provider_name = (
                settings.LLM_PROVIDER
                if settings.LLM_PROVIDER and settings.LLM_PROVIDER in _registered
                else (_registered[0] if _registered else "anthropic")
            )

            provider = None
            # Session-stored model takes precedence over the per-message model sent by the client.
            # This lets PATCH /session/{id}/model switch the model mid-session without the frontend
            # needing to update every outgoing message.
            conv_id_for_lookup = incoming.conversation_id or ""
            session_stored_model = (
                _get_session_model_store().get(conv_id_for_lookup)
                if conv_id_for_lookup
                else None
            )
            effective_model = session_stored_model or incoming.model or ""
            resolved_model = effective_model

            if effective_model:
                mapped = LLMProviderFactory.resolve_provider_for_model(effective_model)
                target_provider_name = mapped or active_provider_name
                try:
                    provider = LLMProviderFactory.create(target_provider_name)
                    resolved_model = effective_model
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
            user_content = incoming.messages[-1].content if incoming.messages else ""
            _intent_hint = ""
            # Populated by orchestrator route(); included in every done frame.
            _routing_metadata: dict = {
                "routing_decision": RoutingDecision.GENERIC_ANSWER.value,
                "skill_name": None,
                "confidence": 0.0,
            }

            # ── route via ChatOrchestrator ────────────────────────────────────
            redis_client = _get_redis()
            store = DataFrameStore(redis_client)
            clarification_state = ClarificationState(redis_client)
            orchestrator = ChatOrchestrator(provider, _get_skill_registry())

            # Resume clarification: if a question was pending, clear it and
            # route based on clarification type.
            pending = clarification_state.get_pending(user_id, conv_id)
            if pending:
                clarification_state.clear(user_id, conv_id)
                clarification_type = pending.get("clarification_type", "agent_question")
                original_query = pending["original_query"]

                if clarification_type == "intent_selection":
                    selected_name = user_content.split(": ", 1)[0].strip()
                    matched_intent = orchestrator.get_intent(selected_name)

                    if matched_intent:
                        resume_prefix = (
                            f"[Original question: {original_query}]\n"
                            f"[User selected intent: {matched_intent.name}"
                            f" — {matched_intent.description}]\n"
                            f"Use the appropriate tool for this intent."
                        )
                        messages_for_loop = [MsgIn(role="user", content=resume_prefix)]
                        use_agent_loop = True
                    else:
                        messages_for_loop = [
                            MsgIn(
                                role="user",
                                content=(
                                    f"The user asked: '{original_query}'. "
                                    f"They clarified: '{user_content}'. "
                                    f"Answer using your general knowledge."
                                ),
                            )
                        ]
                        use_agent_loop = False
                else:
                    resume_prefix = (
                        f"[Original question: {original_query}]\n"
                        f"[Clarification answer: {user_content}]"
                    )
                    messages_for_loop = [
                        MsgIn(role="user", content=resume_prefix),
                        *incoming.messages[:-1],
                        MsgIn(role="user", content=user_content),
                    ]
                    use_agent_loop = True
            else:
                # ── skill routing ─────────────────────────────────────────────
                orch_result = await orchestrator.route(
                    user_message=user_content,
                    session_id=conv_id,
                    model=resolved_model,
                )
                _routing_metadata = {
                    "routing_decision": orch_result.routing_decision.value,
                    "skill_name": orch_result.matched_skill_name,
                    "confidence": orch_result.confidence,
                }

                if orch_result.routing_decision == RoutingDecision.CALL_SKILL:
                    skill_output = (
                        orch_result.skill_result.output if orch_result.skill_result else ""
                    )
                    async with AsyncSessionLocal() as db:
                        _, is_new_conv = await _get_or_create_conversation(
                            db, conv_id, user_id
                        )
                        await _save_messages(
                            db,
                            conv_id,
                            user_content,
                            skill_output,
                            provider.provider_name,
                            resolved_model,
                            max(1, len(skill_output) // 4),
                        )
                    await manager.send_json(
                        {
                            "type": "done",
                            "conversation_id": conv_id,
                            "content": skill_output,
                            "token_count": max(1, len(skill_output) // 4),
                            "provider": provider.provider_name,
                            "model": resolved_model,
                            "routing_metadata": {
                                "routing_decision": orch_result.routing_decision.value,
                                "skill_name": orch_result.matched_skill_name,
                                "confidence": orch_result.confidence,
                            },
                        },
                        websocket,
                    )
                    if is_new_conv and user_content:
                        asyncio.create_task(
                            _generate_and_send_title(
                                websocket, llm_service, user_content, conv_id
                            )
                        )
                    continue

                if orch_result.routing_decision == RoutingDecision.CLARIFY:
                    from app.schemas.ws_messages import WsClarificationRequest

                    clarification_state.set_pending(
                        user_id=user_id,
                        conversation_id=conv_id,
                        question=orch_result.clarification_message or "",
                        candidates=[],
                        original_query=user_content,
                        clarification_type="skill_clarification",
                    )
                    frame = WsClarificationRequest(
                        message=orch_result.clarification_message or "",
                        candidates=[],
                    )
                    await manager.send_json(frame.model_dump(), websocket)
                    async with AsyncSessionLocal() as db:
                        _, is_new_conv = await _get_or_create_conversation(
                            db, conv_id, user_id
                        )
                        await _save_messages(
                            db, conv_id, user_content, "", provider.provider_name, resolved_model, 0
                        )
                    if is_new_conv and user_content:
                        asyncio.create_task(
                            _generate_and_send_title(
                                websocket, llm_service, user_content, conv_id
                            )
                        )
                    continue

                # GENERIC_ANSWER — orchestrator ran is_data_query internally
                messages_for_loop = incoming.messages
                use_agent_loop = orch_result.use_agent_loop
                _intent_hint = orch_result.intent_hint

            # ── pre-loop intent estimation (only on fresh unambiguous data queries) ──
            if use_agent_loop and not pending:
                from app.schemas.ws_messages import WsClarificationRequest

                estimation = orchestrator.estimate_intent(user_content)

                if estimation.confidence == 0.0:
                    use_agent_loop = False
                    # intent_hint already set by orchestrator._generic_answer()
                elif estimation.is_ambiguous and estimation.candidates:
                    clarification_state.set_pending(
                        user_id=user_id,
                        conversation_id=conv_id,
                        question="Which area are you asking about?",
                        candidates=estimation.candidates,
                        original_query=user_content,
                        clarification_type="intent_selection",
                    )
                    frame = WsClarificationRequest(
                        message="I found multiple relevant areas. Which one do you mean?",
                        candidates=estimation.candidates,
                    )
                    await manager.send_json(frame.model_dump(), websocket)
                    async with AsyncSessionLocal() as db:
                        _, is_new_conv = await _get_or_create_conversation(
                            db, conv_id, user_id
                        )
                        await _save_messages(
                            db,
                            conv_id,
                            user_content,
                            "",
                            provider.provider_name,
                            resolved_model,
                            0,
                        )
                    if is_new_conv and user_content:
                        asyncio.create_task(
                            _generate_and_send_title(
                                websocket, llm_service, user_content, conv_id
                            )
                        )
                    continue

            full_content = ""
            is_new_conversation = False

            if use_agent_loop:
                # ── agent tool-use loop ──────────────────────────────────────
                ctx = AgentToolContext(
                    user_id=user_id,
                    conversation_id=conv_id,
                    store=store,
                    clarification_state=clarification_state,
                    websocket=websocket,
                )
                try:
                    loop_result = await provider.run_agent_loop(
                        messages_for_loop, resolved_model, ctx
                    )
                except NotImplementedError:
                    # Provider hasn't implemented run_agent_loop — fall back to stream
                    use_agent_loop = False
                    loop_result = None
                except Exception as exc:
                    logger.error("agent_loop_failed", error=str(exc), user_id=user_id)
                    await manager.send_json(
                        {
                            "type": "error",
                            "message": "Agent error — check server logs",
                            "code": 500,
                        },
                        websocket,
                    )
                    continue

                if use_agent_loop and loop_result is not None:
                    if loop_result.status == "clarification_pending":
                        # WsClarificationRequest was already sent by ask_clarification tool
                        async with AsyncSessionLocal() as db:
                            _, is_new_conversation = await _get_or_create_conversation(
                                db, conv_id, user_id
                            )
                            await _save_messages(
                                db,
                                conv_id,
                                user_content,
                                "",
                                provider.provider_name,
                                resolved_model,
                                0,
                            )
                        if is_new_conversation and user_content:
                            asyncio.create_task(
                                _generate_and_send_title(
                                    websocket, llm_service, user_content, conv_id
                                )
                            )
                        continue

                    formatter = ResponseFormatter(store)
                    agent_response = formatter.build(
                        loop_result,
                        conv_id,
                        user_id,
                        provider.provider_name,
                        resolved_model,
                    )
                    full_content = agent_response.explanation

                    async with AsyncSessionLocal() as db:
                        _, is_new_conversation = await _get_or_create_conversation(
                            db, conv_id, user_id
                        )
                        await _save_messages(
                            db,
                            conv_id,
                            user_content,
                            full_content,
                            provider.provider_name,
                            resolved_model,
                            max(1, len(full_content) // 4),
                        )

                    frame = agent_response.model_dump()
                    frame["routing_metadata"] = _routing_metadata
                    await manager.send_json(frame, websocket)

                    if is_new_conversation and user_content:
                        asyncio.create_task(
                            _generate_and_send_title(
                                websocket, llm_service, user_content, conv_id
                            )
                        )
                    continue

            # ── freeform stream (no tool use) ────────────────────────────────
            full_content = ""
            try:
                async for tok in llm_service.stream(
                    messages_for_loop,
                    resolved_model,
                    incoming.temperature,
                ):
                    full_content += tok
                    await manager.send_json(
                        {"type": "delta", "content": tok}, websocket
                    )

                if _intent_hint:
                    full_content += _intent_hint
                    await manager.send_json(
                        {"type": "delta", "content": _intent_hint}, websocket
                    )

            except Exception as exc:
                logger.error("llm_stream_failed", error=str(exc), user_id=user_id)
                await manager.send_json(
                    {
                        "type": "error",
                        "message": "LLM error — check server logs",
                        "code": 500,
                    },
                    websocket,
                )
                continue

            token_count = max(1, len(full_content) // 4)

            # ── persist to DB before notifying client ────────────────────────
            async with AsyncSessionLocal() as db:
                _, is_new_conversation = await _get_or_create_conversation(
                    db, conv_id, user_id
                )
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
                    "routing_metadata": _routing_metadata,
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
