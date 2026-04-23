from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import structlog
from jwt import InvalidTokenError

from app.core.config import settings

logger = structlog.get_logger()


def create_access_token(user_id: str) -> str:
    """Encode a signed JWT for the given user.

    Args:
        user_id: Opaque user identifier stored in the ``sub`` claim.

    Returns:
        Signed JWT string. Expiry is controlled by ``ACCESS_TOKEN_EXPIRE_DAYS``.
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": user_id, "exp": expire, "iat": datetime.now(timezone.utc)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> str | None:
    """Decode and verify a JWT, returning the subject claim.

    Args:
        token: Encoded JWT string.

    Returns:
        The ``sub`` claim (user ID) if the token is valid and unexpired,
        otherwise ``None``.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        return user_id
    except InvalidTokenError as exc:
        logger.warning("jwt_decode_failed", error=str(exc))
        return None
