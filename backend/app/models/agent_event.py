"""
Agent Event Model Module

This module defines the AgentEvent entity for logging agent runtime events.

Database Attributes:
- id: UUID primary key
- run_id: Identifier linking all events in a single message journey
- agent_id: Optional agent identifier
- chat_id: Telegram chat ID
- user_id: User UUID
- telegram_update_id: Telegram update ID
- event_type: Event type (from EventType enum)
- event_name: Human-readable event name
- step: Optional step identifier within a run
- payload: Flexible JSON payload for event-specific data
- duration_ms: Duration in milliseconds
- success: Whether the operation succeeded
- error_detail: Error message if failed
- created_at: Timestamp

Design:
- Append-only (no UPDATE/DELETE) for audit trail
- JSON payload for flexibility (new event types don't need schema changes)
- Indexed on run_id, chat_id, event_type, created_at for efficient queries
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class AgentEvent(Base):
    """
    AgentEvent model for tracking agent runtime events.

    Useful for:
    - Debugging agent behavior
    - Analyzing performance (duration_ms)
    - Full replay of agent runs
    - Cost tracking (LLM calls, tool calls)
    - Error tracking and analysis
    """

    __tablename__ = "agent_events"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the event"
    )

    run_id = Column(
        String(100),
        nullable=False,
        index=True,
        doc="Run identifier - links all events in a single message journey"
    )

    agent_id = Column(
        String(100),
        nullable=True,
        index=True,
        doc="Agent identifier (optional)"
    )

    chat_id = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Telegram chat ID"
    )

    user_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        doc="User UUID"
    )

    telegram_update_id = Column(
        String(50),
        nullable=True,
        doc="Telegram update ID"
    )

    event_type = Column(
        String(50),
        nullable=False,
        index=True,
        doc="Event type (from EventType enum)"
    )

    event_name = Column(
        String(100),
        nullable=False,
        doc="Human-readable event name"
    )

    step = Column(
        String(50),
        nullable=True,
        doc="Optional step identifier within a run"
    )

    payload = Column(
        JSON,
        nullable=False,
        default=dict,
        doc="Flexible JSON payload for event-specific data"
    )

    duration_ms = Column(
        Integer,
        nullable=True,
        doc="Duration in milliseconds"
    )

    success = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the operation succeeded"
    )

    error_detail = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the event was created"
    )

    __table_args__ = (
        Index("idx_agent_events_chat_id_step", "chat_id", "step"),
        Index("idx_agent_events_type_created", "event_type", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AgentEvent(run_id={self.run_id}, event_type={self.event_type}, success={self.success})>"