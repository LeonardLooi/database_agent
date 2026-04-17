# FastAPI Auth & Security Patterns

Production-ready authentication and authorization patterns for Python 3.14 + FastAPI.
All patterns use FastAPI `Depends()` injection — no middleware monkey-patching.

---

## Dependencies

```bash
uv add "python-jose[cryptography]" "passlib[bcrypt]" python-multipart
# python-multipart required for OAuth2PasswordRequestForm
```

`pyproject.toml` pin:
```toml
[project]
dependencies = [
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.9",
]
```

---

## 1. Configuration

```python
# src/my_service/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    jwt_secret_key: str           # min 32 chars — set via env var
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    model_config = {"env_file": ".env"}

settings = Settings()
```

> **Note:** For service-to-service auth or public key distribution, use RS256:
> set `jwt_algorithm = "RS256"` and provide `jwt_private_key` / `jwt_public_key` paths.
> HS256 is appropriate for single-service internal auth; RS256 matches the NestJS workspace standard.

---

## 2. Password Hashing

```python
# src/my_service/core/security.py
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
```

**Rule:** bcrypt cost factor 12 minimum. Never store or log plaintext passwords.

---

## 3. JWT Token Service

```python
# src/my_service/core/tokens.py
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from .config import settings

def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(subject: str) -> str:
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    """Raises JWTError on invalid/expired token."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
```

---

## 4. OAuth2 Bearer — Current User Dependency

```python
# src/my_service/api/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from ..core.tokens import decode_token
from ..models.user import UserInDB
from ..services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(),
) -> UserInDB:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exc
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = await user_service.get_by_id(user_id)
    if user is None:
        raise credentials_exc
    return user
```

---

## 5. Auth Routes

```python
# src/my_service/api/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ...core.security import verify_password, hash_password
from ...core.tokens import create_access_token, create_refresh_token
from ...models.auth import TokenResponse, RegisterRequest
from ...services.user_service import UserService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

@router.post("/token", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(),
) -> TokenResponse:
    user = await user_service.get_by_email(form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(str(user.id), {"role": user.role}),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
    )

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    user_service: UserService = Depends(),
) -> dict:
    existing = await user_service.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    await user_service.create(body.email, hash_password(body.password))
    return {"message": "Account created"}
```

---

## 6. Auth Models

```python
# src/my_service/models/auth.py
from pydantic import BaseModel, EmailStr, Field

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
```

---

## 7. RBAC — Role-Based Access Control

```python
# src/my_service/core/rbac.py
from enum import StrEnum
from fastapi import Depends, HTTPException, status
from .deps import get_current_user
from ..models.user import UserInDB

class Role(StrEnum):
    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN  = "admin"

# Hierarchy: higher index = more access
_ROLE_RANK = {Role.VIEWER: 0, Role.EDITOR: 1, Role.ADMIN: 2}

def require_role(minimum: Role):
    """FastAPI dependency — enforces minimum role rank."""
    async def _check(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if _ROLE_RANK.get(current_user.role, -1) < _ROLE_RANK[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {minimum}",
            )
        return current_user
    return _check
```

**Usage:**

```python
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserInDB = Depends(require_role(Role.ADMIN)),
) -> dict:
    ...
```

---

## 8. PBAC — Permission-Based Access Control

```python
# src/my_service/core/pbac.py
from enum import StrEnum
from fastapi import Depends, HTTPException, status
from .rbac import Role
from .deps import get_current_user
from ..models.user import UserInDB

class Permission(StrEnum):
    READ_REPORTS   = "read:reports"
    WRITE_REPORTS  = "write:reports"
    MANAGE_USERS   = "manage:users"
    BILLING_ACCESS = "billing:access"

ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.VIEWER: {Permission.READ_REPORTS},
    Role.EDITOR: {Permission.READ_REPORTS, Permission.WRITE_REPORTS},
    Role.ADMIN:  {p for p in Permission},  # all permissions
}

def require_permission(permission: Permission):
    async def _check(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        allowed = ROLE_PERMISSIONS.get(current_user.role, set())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return current_user
    return _check
```

**Usage:**

```python
@router.get("/reports")
async def list_reports(
    current_user: UserInDB = Depends(require_permission(Permission.READ_REPORTS)),
) -> list[ReportResponse]:
    ...
```

---

## 9. Resource Ownership

```python
# src/my_service/api/deps.py (add to existing file)
async def require_ownership(
    resource_user_id: str,
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """Allow access only if user owns the resource OR is admin."""
    if str(current_user.id) != resource_user_id and current_user.role != Role.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return current_user
```

**Usage in a route:**

```python
@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    doc_service: DocumentService = Depends(),
    current_user: UserInDB = Depends(get_current_user),
) -> DocumentResponse:
    doc = await doc_service.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    await require_ownership(doc.owner_id, current_user)
    return DocumentResponse.model_validate(doc)
```

---

## 10. Rate Limiting on Auth Endpoints

Integrate with `fastapi-rate-limiting.md` — use these limits for auth routes specifically:

```python
# Tighter limits than general API endpoints
@router.post("/token")
@limiter.limit("5/minute")          # 5 login attempts per minute per IP
async def login(request: Request, ...): ...

@router.post("/register")
@limiter.limit("3/hour")            # 3 registrations per hour per IP
async def register(request: Request, ...): ...

@router.post("/password-reset")
@limiter.limit("3/hour")            # prevent email enumeration via timing
async def password_reset(request: Request, ...): ...
```

---

## 11. Security Rules

| Rule | Detail |
|------|--------|
| **bcrypt rounds** | Minimum 12 (`bcrypt__rounds=12` in `CryptContext`) |
| **Token expiry** | Access: 15 min max; Refresh: 7 days max |
| **Token type claim** | Always validate `payload["type"] == "access"` before accepting |
| **No plaintext** | Never log, store, or return plaintext passwords or tokens |
| **401 vs 403** | 401 = unauthenticated (no/invalid token); 403 = authenticated but unauthorized |
| **Password reset** | Rate-limit to 3/hour; return same response whether email exists or not (prevent enumeration) |
| **HTTPS only** | Set `Secure` cookie flag; enforce HTTPS in production via reverse proxy |
| **Algorithm pinning** | Always pass `algorithms=[settings.jwt_algorithm]` to `jwt.decode()` — never omit |

---

## 12. Testing Auth

```python
# tests/test_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.my_service.main import app
from src.my_service.core.security import hash_password

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest.mark.asyncio
async def test_login_success(client, seed_user):
    resp = await client.post("/api/v1/auth/token", data={
        "username": seed_user.email,
        "password": "correct-password",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_user):
    resp = await client.post("/api/v1/auth/token", data={
        "username": seed_user.email,
        "password": "wrong",
    })
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_protected_route_no_token(client):
    resp = await client.get("/api/v1/users/me")
    assert resp.status_code == 401

@pytest.mark.asyncio
async def test_rbac_insufficient_role(client, viewer_token):
    resp = await client.delete(
        "/api/v1/users/some-id",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert resp.status_code == 403
```
