---
name: pydantic-models-py
description: Pydantic v2 multi-model pattern for clean API contracts — Base, Create, Update, Response variants with camelCase aliases and PATCH support. Use when defining FastAPI request/response schemas or data validation models.
allowed-tools: Read, Write, Edit
metadata:
  triggers: Pydantic models, API schema, request body, response model, Pydantic BaseModel, data validation, PATCH endpoint, camelCase alias, API contract, request/response schema
  related-skills: python-dev, openapi-spec-generation, api-design-principles
  domain: backend
  role: specialist
  scope: implementation
  output-format: code
last-reviewed: "2026-03-14"
---

## Iron Law

**NEVER USE A SINGLE PYDANTIC MODEL FOR BOTH CREATE AND RESPONSE — separate contracts prevent leaking internal fields, block over-posting, and make API evolution safe**

# Pydantic v2 Models

Create Pydantic models following the multi-model pattern for clean, safe API contracts.

## Multi-Model Pattern

| Model | Purpose | Required Fields |
|-------|---------|-----------------|
| `Base` | Common fields shared across all variants | Shared, validated fields |
| `Create` | POST request body — fields the client supplies | Required fields only |
| `Update` | PATCH request body — partial update | All optional (use `None` default) |
| `Response` | API response — all fields the client sees | Includes id, timestamps |
| `InDB` | Internal/repository layer — DO NOT expose directly | DB-only fields (e.g., hashed passwords) |

---

## Full Pattern Example

```python
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


# ── Base: shared validated fields ──────────────────────────────────────────
class UserBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")


# ── Create: POST /users body ────────────────────────────────────────────────
class UserCreate(UserBase):
    """Request body for user creation. Never include id or timestamps."""
    password: str = Field(..., min_length=8)


# ── Update: PATCH /users/{id} body ─────────────────────────────────────────
class UserUpdate(BaseModel):
    """All fields optional — client sends only what changes."""
    name: str | None = Field(None, min_length=1, max_length=100)
    email: str | None = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$")


# ── Response: GET /users or POST /users response ────────────────────────────
class UserResponse(UserBase):
    """What the API returns. Never include password or internal fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)  # ORM compatibility


# ── InDB: internal repository layer only ────────────────────────────────────
class UserInDB(UserResponse):
    """Internal model for repository layer. NEVER return this from a route."""
    hashed_password: str
```

---

## camelCase Aliases (for JS/TS clients)

```python
from pydantic import BaseModel, Field, ConfigDict


class UserResponse(BaseModel):
    workspace_id: str = Field(..., alias="workspaceId")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,  # Accept both snake_case and camelCase on input
    )
```

Use `model.model_dump(by_alias=True)` when serializing for JSON responses to emit camelCase.

---

## PATCH Endpoint — Partial Update Pattern

```python
from pydantic import BaseModel, Field


class ProjectUpdate(BaseModel):
    """All fields optional for PATCH requests. None means 'do not change'."""
    name: str | None = Field(None, min_length=1)
    description: str | None = None
    is_active: bool | None = None
```

In the service layer, apply only the non-None fields:

```python
async def update_project(id: UUID, payload: ProjectUpdate, session: AsyncSession) -> Project:
    project = await session.get(Project, id)
    update_data = payload.model_dump(exclude_unset=True)  # Only fields client sent
    for field, value in update_data.items():
        setattr(project, field, value)
    await session.commit()
    await session.refresh(project)
    return project
```

---

## PostgreSQL / SQLAlchemy Integration

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, func
from uuid import UUID
import uuid


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# Convert ORM → Pydantic Response (model_config from_attributes=True required)
user_response = UserResponse.model_validate(user_orm_instance)
```

---

## Integration Steps

1. Create models in `src/<service>/schemas/<resource>.py`
2. Export from `src/<service>/schemas/__init__.py`
3. Import in routes: `from src.<service>.schemas.<resource> import UserCreate, UserResponse`
4. Use `Create` as request body param, `Response` as return type annotation
5. Use `model_validate(orm_obj)` in service layer to convert ORM → Response

---

## Naming Conventions

| Model | Naming Pattern | Example |
|-------|---------------|---------|
| Base | `{Resource}Base` | `UserBase` |
| Create | `{Resource}Create` | `UserCreate` |
| Update | `{Resource}Update` | `UserUpdate` |
| Response | `{Resource}Response` | `UserResponse` |
| InDB | `{Resource}InDB` | `UserInDB` |

---

## Hard Prohibitions

- Never return `InDB` from a route handler — it contains internal fields (hashed passwords, etc.)
- Never use `Optional[str]` — use `str | None` (Python 3.10+ union syntax)
- Never use `@validator` — this is Pydantic v1 syntax; use `@field_validator` in v2
- Never use `orm_mode = True` — use `model_config = ConfigDict(from_attributes=True)` in v2
- Never skip `exclude_unset=True` in PATCH service logic — it distinguishes "not sent" from `null`
