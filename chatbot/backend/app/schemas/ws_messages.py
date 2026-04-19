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


# ── agent frames (data query responses) ──────────────────────────────────────

class WsAgentProgress(BaseModel):
    """Sent during agent loop execution to keep the client informed."""
    type: Literal["agent_progress"] = "agent_progress"
    step: str
    message: str


class WsClarificationRequest(BaseModel):
    """Sent when the agent cannot confidently match an intent and needs user input."""
    type: Literal["clarification_request"] = "clarification_request"
    message: str
    candidates: list[str] = Field(default_factory=list)


class WsAgentResponse(BaseModel):
    """Final structured response from the agent loop after data retrieval."""
    type: Literal["agent_response"] = "agent_response"
    conversation_id: str
    explanation: str
    table_md: str
    csv: str
    sql_used: list[str] = Field(default_factory=list)
    python_used: str = ""
    truncated: bool = False
    row_count: int = 0
    provider: str
    model: str
