"""
User Model Module

This module defines the User entity for the Tower Project application.
Users are the primary actors in the system, engaging in conversations
and managing documents.

Database Attributes:
- id: UUID primary key
- email: Unique email address (used for authentication)
- password_hash: Securely hashed password
- name: Display name
- created_at: Account creation timestamp
- last_login: Last successful login timestamp

Relationships:
- User has many Conversations (one-to-many)
- User has many Messages (one-to-many)
- User has many Documents (one-to-many)

Qdrant Integration:
- User embeddings are NOT mandatory for MVP
- Future versions may include user embedding for personalization
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
import uuid

from app.models.database import Base


class User(Base):
    """
    User model representing application users.

    This model stores user account information including
    authentication credentials and profile data.

    Attributes:
        id: Unique identifier (UUID4)
        email: User's email address (unique, used for login)
        password_hash: Bcrypt hash of user's password
        name: User's display name
        created_at: Timestamp when account was created
        last_login: Timestamp of last login (nullable)

    Relationships:
        conversations: All conversations created by this user
        messages: All messages sent by this user
        documents: All documents owned by this user

    Example:
        user = User(
            email="user@example.com",
            password_hash=bcrypt_hash,
            name="John Doe"
        )
    """

    # Table name in PostgreSQL
    __tablename__ = "users"

    # Primary key using UUID for global uniqueness and security
    # UUID4 provides 122 bits of randomness for unique identifiers
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the user account"
    )

    # User's email address - unique constraint ensures one account per email
    # Indexed for fast lookup during authentication
    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="User's email address, used for authentication"
    )

    # Hashed password using bcrypt
    # Never store plain text passwords - always hash before storage
    password_hash = Column(
        String(255),
        nullable=False,
        doc="Bcrypt hash of the user's password"
    )

    # User's display name for UI presentation
    name = Column(
        String(100),
        nullable=False,
        doc="User's display name"
    )

    # Account creation timestamp
    # Defaults to current timestamp when record is created
    # server_default=func.now() ensures database-level default
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Timestamp when the user account was created"
    )

    # Last successful login timestamp
    # Nullable because new users haven't logged in yet
    last_login = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of the user's last successful login"
    )

    telegram_chat_id = Column(
        String(50),
        nullable=True,
        index=True,
        doc="Telegram chat ID for notifications"
    )

    telegram_link_token = Column(
        String(64),
        nullable=True,
        doc="Temporary token for linking Telegram account"
    )

    preferences = Column(
        JSONB,
        nullable=True,
        default=dict,
        doc="User preferences stored as JSON"
    )

    # Relationships with other models
    # cascade="all, delete-orphan" ensures related records are deleted
    # when the user is deleted

    # All conversations created by this user
    conversations = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="All conversations owned by this user"
    )

    # All messages sent by this user
    # Messages have role='user' in the Message model
    messages = relationship(
        "Message",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="All messages sent by this user"
    )

    # All documents uploaded by this user
    documents = relationship(
        "Document",
        back_populates="user",
        cascade="all, delete-orphan",
        doc="All documents owned by this user"
    )

    def __repr__(self) -> str:
        """
        String representation of the User object.

        Returns:
            String representation showing email and name.
        """
        return f"<User(email={self.email}, name={self.name})>"