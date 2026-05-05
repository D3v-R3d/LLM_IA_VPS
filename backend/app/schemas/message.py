from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageBase(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)


class MessageCreate(MessageBase):
    conversation_id: UUID


class MessageUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=1)


class MessageResponse(MessageBase):
    id: UUID
    user_id: UUID
    conversation_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True