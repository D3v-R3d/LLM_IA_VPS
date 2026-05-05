from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate


class ConversationService:
    def get_by_id(self, db: Session, conversation_id: UUID) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_by_user(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return db.query(Conversation).offset(skip).limit(limit).all()

    def get_by_telegram_chat_id(self, db: Session, telegram_chat_id: str) -> Optional[Conversation]:
        return db.query(Conversation).filter(
            Conversation.telegram_chat_id == telegram_chat_id
        ).first()