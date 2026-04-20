from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
import structlog.dev
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import create_tables


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if settings.DEBUG else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(10 if settings.DEBUG else 20),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _configure_logging()
    logger = structlog.get_logger()
    from app.services.llm.factory import LLMProviderFactory
    available = [p["provider"] for p in LLMProviderFactory.get_providers_data()]
    logger.info("startup", version=settings.APP_VERSION, provider=settings.LLM_PROVIDER, available_providers=available)
    await create_tables()
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Chatbot API",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.CORS_ORIGIN, "http://localhost:4200", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import auth, chat_ws, conversations, health  # noqa: E402

app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(health.router)
app.include_router(chat_ws.router)
