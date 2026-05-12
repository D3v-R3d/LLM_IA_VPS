from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class UserModelPrefsBase(BaseModel):
    provider: str = "ollama"
    model: str = "gemma4:31b"
    is_local: bool = True
    current_session: Optional[str] = None
    embedding_model: Optional[str] = "nomic-embed-text"


class UserModelPrefsCreate(UserModelPrefsBase):
    pass


class UserModelPrefsUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    is_local: Optional[bool] = None
    current_session: Optional[str] = None
    embedding_model: Optional[str] = None


class UserModelPrefsResponse(UserModelPrefsBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True