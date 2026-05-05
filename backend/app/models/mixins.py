"""
Base Mixins for Database Models

Provides reusable model components:
- TimestampMixin: created_at field
"""

from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin for created_at timestamp field."""

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the record was created"
    )