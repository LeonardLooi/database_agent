from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.ws_manager import manager
from app.services.llm.factory import LLMProviderFactory

logger = structlog.get_logger()
router = APIRouter(tags=["health"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict:
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("health_db_check_failed", error=str(exc))
        db_status = "error"

    available = LLMProviderFactory.get_providers_data()

    return {
        "status": "ok",
        "db": db_status,
        "ws_connections": manager.connection_count,
        "active_provider": settings.LLM_PROVIDER,
        "available_providers": [p["provider"] for p in available],
        "version": settings.APP_VERSION,
    }
