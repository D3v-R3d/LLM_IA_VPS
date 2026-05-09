"""
LLM Log Model Module

This module defines the LlmLog entity for logging LLM interactions.

Database Attributes:
- id: UUID primary key
- user_id: Foreign key to User
- conversation_id: Foreign key to Conversation (optional)
- chat_id: Telegram chat ID if applicable
- message: User input message
- response_text: LLM response content
- model: Model used (e.g., gemma-4-31b-it)
- provider: Provider (e.g., google)
- tools_sent: JSON array of tools sent to LLM
- tool_calls: JSON array of tools called by LLM
- tokens_input: Number of input tokens
- tokens_output: Number of output tokens
- duration_ms: Duration in milliseconds
- iterations: Number of LLM iterations
- intent: Detected intent (optional)
- success: Whether the call succeeded
- error: Error message if failed
- created_at: Timestamp
"""

from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class LlmLog(Base):
    """
    LLM Log model for tracking LLM interactions.

    Useful for:
    - Debugging LLM behavior
    - Analyzing performance
    - Cost tracking (tokens)
    - Improving prompts
    """

    __tablename__ = "llm_logs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the log entry"
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Foreign key to User (optional)"
    )

    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Foreign key to Conversation"
    )

    chat_id = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Telegram chat ID"
    )

    message = Column(
        Text,
        nullable=False,
        doc="User input message"
    )

    response_text = Column(
        Text,
        nullable=True,
        doc="LLM response content"
    )

    model = Column(
        String(100),
        nullable=False,
        doc="Model used (e.g., gemma-4-31b-it)"
    )

    provider = Column(
        String(50),
        nullable=False,
        doc="Provider (e.g., google)"
    )

    tools_sent = Column(
        JSON,
        nullable=True,
        doc="Array of tools sent to LLM"
    )

    tool_calls = Column(
        JSON,
        nullable=True,
        doc="Array of tools called by LLM"
    )

    tokens_input = Column(
        Integer,
        nullable=True,
        doc="Number of input tokens"
    )

    tokens_output = Column(
        Integer,
        nullable=True,
        doc="Number of output tokens"
    )

    duration_ms = Column(
        Integer,
        nullable=True,
        doc="Duration in milliseconds"
    )

    iterations = Column(
        Integer,
        nullable=False,
        default=1,
        doc="Number of LLM iterations"
    )

    intent = Column(
        String(100),
        nullable=True,
        doc="Detected intent"
    )

    success = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the call succeeded"
    )

    error = Column(
        Text,
        nullable=True,
        doc="Error message if failed"
    )

    error_code = Column(
        String(20),
        nullable=True,
        doc="HTTP status code (e.g., 500, 429)"
    )

    error_body = Column(
        Text,
        nullable=True,
        doc="Full error response body for debugging"
    )

    error_url = Column(
        String(500),
        nullable=True,
        doc="URL that failed"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the log was created"
    )

    user = relationship("User", doc="The User who made the request")
    conversation = relationship("Conversation", doc="The Conversation")

    def __repr__(self) -> str:
        return f"<LlmLog(model={self.model}, success={self.success}, duration={self.duration_ms}ms)>"