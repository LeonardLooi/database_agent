from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.agent.session_model_store import SessionModelStore
from app.core.config import settings
from app.core.security import decode_token
from app.services.llm.factory import MODEL_TO_PROVIDER

logger = structlog.get_logger()
router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Shared in-memory store (Redis wired in if REDIS_ENABLED)
_store: SessionModelStore | None = None


def _get_store() -> SessionModelStore:
    global _store
    if _store is None:
        redis_client = None
        if settings.REDIS_ENABLED:
            import redis as redis_lib

            redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
        _store = SessionModelStore(redis_client)
    return _store


class ModelSwitchRequest(BaseModel):
    model: str


class ModelSwitchResponse(BaseModel):
    model: str
    provider: str
    session_id: str


@router.patch("/{session_id}/model", response_model=ModelSwitchResponse)
async def switch_session_model(
    session_id: str,
    body: ModelSwitchRequest,
    token: str = Query(...),
) -> ModelSwitchResponse:
    """Switch the active model for a conversation session.

    Validates the model against known providers, persists the preference,
    and returns the resolved provider name.  Session history is preserved —
    only the model used for subsequent messages changes.

    Args:
        session_id: Conversation ID (used as the session key).
        body: JSON body containing `model` string.
        token: JWT bearer token passed as query parameter.

    Returns:
        ModelSwitchResponse with model, provider, and session_id.

    Raises:
        401 if the token is invalid.
        400 if the model is not in the supported model list.
    """
    user_id = decode_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    provider_name = MODEL_TO_PROVIDER.get(body.model)
    if not provider_name:
        supported = sorted(MODEL_TO_PROVIDER)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{body.model}'. Supported: {supported}",
        )

    _get_store().set(session_id, body.model)

    logger.info(
        "session_model_switched",
        session_id=session_id,
        model=body.model,
        provider=provider_name,
        user_id=user_id,
    )

    return ModelSwitchResponse(
        model=body.model,
        provider=provider_name,
        session_id=session_id,
    )
