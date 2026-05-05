"""
Models Package

This package contains SQLAlchemy ORM models for the Tower Project application.

Models:
- User: Application user accounts
- Conversation: Chat sessions between user and LLM
- Message: Individual messages in a conversation
- Document: User-uploaded files for RAG processing

Usage:
    from app.models import User, Conversation, Message, Document

    # Access relationships
    user = db.query(User).first()
    for conversation in user.conversations:
        for message in conversation.messages:
            print(message.content)
"""

from app.models.database import Base, get_db, SessionLocal, engine
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message, MessageRole
from app.models.document import Document

__all__ = [
    "Base",
    "get_db",
    "SessionLocal",
    "engine",
    "User",
    "Conversation",
    "Message",
    "MessageRole",
    "Document",
]