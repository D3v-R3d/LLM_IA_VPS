"""
Base Schemas for API Request/Response Validation

Provides reusable schema components:
- ResponseBase: Common response fields + Config(from_attributes=True)
"""

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class ResponseBase(BaseModel):
    """Base schema for all response models with common config."""

    model_config = ConfigDict(from_attributes=True)


class TimestampResponse(ResponseBase):
    """Response with standard timestamp fields."""

    id: UUID
    user_id: UUID
    created_at: datetime
