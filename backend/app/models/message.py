"""
Message Model Module

This module defines the Message entity for the Tower Project application.
Messages are the core unit of communication in conversations.

Database Attributes:
- id: UUID primary key
- user_id: Foreign key to User
- conversation_id: Foreign key to Conversation
- role: Enum (user | assistant)
- content: Text content of the message
- created_at: Creation timestamp

Qdrant Integration:
- YES - Message content is embedded
- Text embedded: message content
- Payload: message_id, user_id, conversation_id, role, timestamp
"""

from sqlalchemy import Column, String, DateTime, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.models.database import Base


class MessageRole(str, enum.Enum):
    """
    Enum representing the role of a message sender.

    Values:
        USER: Message from the human user
        ASSISTANT: Message from the LLM assistant
    """
    USER = "user"
    ASSISTANT = "assistant"


class Message(Base):
    """
    Message model representing a single message in a conversation.

    Messages are the fundamental unit of communication, containing
    the actual text content exchanged between user and assistant.

    Attributes:
        id: Unique identifier (UUID4)
        user_id: Foreign key to the User who sent this message
        conversation_id: Foreign key to the parent Conversation
        role: Role of the sender (user or assistant)
        content: The actual text content of the message
        created_at: Timestamp when the message was created

    Relationships:
        user: The User who sent this message
        conversation: The Conversation this message belongs to

    Qdrant Storage:
        This model's content should be embedded and stored in Qdrant
        for semantic search capabilities.

    Example:
        message = Message(
            user_id=user_uuid,
            conversation_id=conversation_uuid,
            role=MessageRole.USER,
            content="Hello, how are you?"
        )
    """

    # Table name in PostgreSQL
    __tablename__ = "messages"

    # Primary key using UUID for global uniqueness
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the message"
    )

    # Foreign key to User table
    # Indexed for fast lookup of user's messages
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the User who sent this message"
    )

    # Foreign key to Conversation table
    # Indexed for fast lookup of conversation messages
    conversation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the Conversation this message belongs to"
    )

    # Role enum for message sender
    # Using PostgreSQL ENUM type for efficient storage
    role = Column(
        Enum(MessageRole, name="message_role", create_constraint=True),
        nullable=False,
        doc="Role of the message sender (user or assistant)"
    )

    # Message content - using Text type for potentially long content
    # No max length to accommodate long-form responses
    content = Column(
        Text,
        nullable=False,
        doc="The text content of the message"
    )

    # Message creation timestamp
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the message was created"
    )

    # Relationships
    # back_populates links to corresponding attributes in related models

    # Relationship to User
    user = relationship(
        "User",
        back_populates="messages",
        doc="The User who sent this message"
    )

    # Relationship to Conversation
    conversation = relationship(
        "Conversation",
        back_populates="messages",
        doc="The Conversation this message belongs to"
    )

    def __repr__(self) -> str:
        """
        String representation of the Message object.

        Returns:
            String representation showing role and truncated content.
        """
        content_preview = (
            self.content[:50] + "..."
            if len(self.content) > 50
            else self.content
        )
        return f"<Message(role={self.role.value}, content={content_preview})>"