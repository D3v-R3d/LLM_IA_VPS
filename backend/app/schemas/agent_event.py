from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Dict, Any


class AgentEventBase(BaseModel):
    run_id: str
    event_type: str
    event_name: str
    success: bool = True


class AgentEventCreate(AgentEventBase):
    agent_id: Optional[str] = None
    chat_id: Optional[str] = None
    user_id: Optional[UUID] = None
    telegram_update_id: Optional[str] = None
    step: Optional[str] = None
    payload: Dict[str, Any] = {}
    duration_ms: Optional[int] = None
    error_detail: Optional[str] = None


class AgentEventResponse(AgentEventBase):
    id: UUID
    agent_id: Optional[str] = None
    chat_id: Optional[str] = None
    user_id: Optional[UUID] = None
    telegram_update_id: Optional[str] = None
    step: Optional[str] = None
    payload: Dict[str, Any] = {}
    duration_ms: Optional[int] = None
    error_detail: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True