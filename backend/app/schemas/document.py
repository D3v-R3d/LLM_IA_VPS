from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class DocumentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: str = Field(..., min_length=1, max_length=20)


class DocumentCreate(DocumentBase):
    content_raw: str


class DocumentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    content_raw: Optional[str] = None


class DocumentResponse(DocumentBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    is_embedded: bool = False

    class Config:
        from_attributes = True