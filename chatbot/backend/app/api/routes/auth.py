from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.security import create_access_token

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])


class GuestTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str


@router.post("/guest", response_model=GuestTokenResponse)
async def guest_login() -> GuestTokenResponse:
    """Issue a JWT for a new anonymous guest session."""
    user_id = f"guest_{uuid.uuid4().hex[:12]}"
    token = create_access_token(user_id)
    logger.info("guest_token_issued", user_id=user_id)
    return GuestTokenResponse(access_token=token, user_id=user_id)


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/token", response_model=GuestTokenResponse)
async def login(body: LoginRequest) -> GuestTokenResponse:
    """Demo login — username becomes the user_id, any password accepted."""
    if not body.username:
        raise HTTPException(status_code=400, detail="username required")
    user_id = f"user_{body.username}"
    token = create_access_token(user_id)
    logger.info("user_token_issued", user_id=user_id)
    return GuestTokenResponse(access_token=token, user_id=user_id)
