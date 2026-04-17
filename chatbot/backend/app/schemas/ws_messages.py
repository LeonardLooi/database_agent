from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MsgIn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class WsIncoming(BaseModel):
    type: Literal["message", "ping"]
    conversation_id: str = ""
    messages: list[MsgIn] = Field(default_factory=list)
    model: str = ""
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


# ── outgoing frames ──────────────────────────────────────────────────────────

class WsDelta(BaseModel):
    type: Literal["delta"] = "delta"
    content: str


class WsDone(BaseModel):
    type: Literal["done"] = "done"
    conversation_id: str
    token_count: int
    provider: str
    model: str


class WsError(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: int


class WsPong(BaseModel):
    type: Literal["pong"] = "pong"


class WsTitle(BaseModel):
    type: Literal["title"] = "title"
    conversation_id: str
    title: str


class WsProviderInfo(BaseModel):
    provider: str
    models: list[str]
    default_model: str


class WsProviders(BaseModel):
    type: Literal["providers"] = "providers"
    data: list[WsProviderInfo]
