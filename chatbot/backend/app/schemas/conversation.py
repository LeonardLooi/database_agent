from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    provider: str
    model: str
    token_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationOut(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationWithMessages(ConversationOut):
    messages: list[MessageOut] = []
