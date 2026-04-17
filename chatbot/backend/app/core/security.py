from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import structlog
from jwt import InvalidTokenError

from app.core.config import settings

logger = structlog.get_logger()


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        return user_id
    except InvalidTokenError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        return None
