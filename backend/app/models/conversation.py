"""
Conversation Model Module

This module defines the Conversation entity for the Tower Project application.
Conversations are containers for messages between users and the LLM.

Database Attributes:
- id: UUID primary key
- user_id: Foreign key to User
- title: Optional conversation title
- created_at: Creation timestamp
- updated_at: Last modification timestamp

Relationships:
- Conversation belongs to one User (many-to-one)
- Conversation has many Messages (one-to-many)

Qdrant Integration:
- Conversation embeddings are recommended
- Embeds the conversation summary or last context messages
- Payload includes: conversation_id, user_id, last_summary, updated_at
"""

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class Conversation(Base):
    """
    Conversation model representing a chat session.

    A conversation contains multiple messages exchanged between
    the user and the LLM assistant.

    Attributes:
        id: Unique identifier (UUID4)
        user_id: Foreign key to the User who owns this conversation
        title: Optional title for easy identification
        created_at: Timestamp when conversation was created
        updated_at: Timestamp when conversation was last modified

    Relationships:
        user: The User who owns this conversation
        messages: All messages in this conversation (ordered by created_at)

    Example:
        conversation = Conversation(
            user_id=user_uuid,
            title="Discussion about Python"
        )
    """

    # Table name in PostgreSQL
    __tablename__ = "conversations"

    # Primary key using UUID for global uniqueness
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the conversation"
    )

    # Foreign key to User table
    # Indexed for fast lookup of user's conversations
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the User who owns this conversation"
    )

    # Optional conversation title for easy identification
    # Max length 255 characters for titles
    title = Column(
        String(255),
        nullable=True,
        doc="Optional title for the conversation"
    )

    # Conversation creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the conversation was created"
    )

    # Last modification timestamp
    # Updated automatically when messages are added or title changes
    # Uses server_default for initial value and onupdate for updates
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Timestamp when the conversation was last modified"
    )

    telegram_chat_id = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Telegram chat ID if this is a Telegram conversation"
    )

    # Relationship to User
    # back_populates="conversations" links to User.conversations
    user = relationship(
        "User",
        back_populates="conversations",
        doc="The User who owns this conversation"
    )

    # Relationship to Messages
    # cascade="all, delete-orphan" ensures messages are deleted
    # when conversation is deleted
    # order_by="Message.created_at" maintains chronological order
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        doc="All messages in this conversation, ordered chronologically"
    )

    def __repr__(self) -> str:
        """
        String representation of the Conversation object.

        Returns:
            String representation showing title or first message preview.
        """
        title_or_id = self.title or str(self.id)[:8]
        return f"<Conversation(title={title_or_id}, user_id={self.user_id})>"