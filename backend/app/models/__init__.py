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
from app.models.user_model_prefs import UserModelPrefs
from app.models.agent_event import AgentEvent
import logging

logger = logging.getLogger(__name__)

# Create all tables (idempotent - only creates missing tables)
Base.metadata.create_all(bind=engine)

# Initialize Qdrant collections
try:
    from app.services.qdrant_init import init_qdrant_collections
    init_qdrant_collections()
except Exception as e:
    logger.warning(f"Qdrant init skipped: {e}")

# Initialize Tool Registry (Qdrant indexing)
try:
    from app.services.tool_registry import init_tool_registry
    init_tool_registry()
except Exception as e:
    logger.warning(f"Tool registry init skipped: {e}")

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
    "UserModelPrefs",
    "AgentEvent",
]