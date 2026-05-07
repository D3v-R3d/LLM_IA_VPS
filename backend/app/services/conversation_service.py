from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.models.conversation import Conversation
from app.schemas.conversation import ConversationCreate, ConversationUpdate
from app.services.base_service import BaseService


class ConversationService(BaseService[Conversation]):
    def __init__(self):
        super().__init__(Conversation)

    def get_by_id(self, db: Session, conversation_id: UUID) -> Optional[Conversation]:
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()

    def get_all(self, db: Session, user_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[Conversation]:
        query = db.query(Conversation)
        if user_id:
            query = query.filter(Conversation.user_id == user_id)
        return query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

    def get_by_user(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()

    def get_by_telegram_chat_id(self, db: Session, telegram_chat_id: str) -> Optional[Conversation]:
        return db.query(Conversation).filter(
            Conversation.telegram_chat_id == telegram_chat_id
        ).first()

    def create(
        self,
        db: Session,
        user_id: UUID,
        conversation_data: ConversationCreate,
        telegram_chat_id: Optional[str] = None
    ) -> Conversation:
        db_conversation = Conversation(
            user_id=user_id,
            title=conversation_data.title or "New Conversation",
            telegram_chat_id=telegram_chat_id
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    def update(self, db: Session, conversation_id: UUID, conversation_data: ConversationUpdate) -> Optional[Conversation]:
        db_conversation = self.get_by_id(db, conversation_id)
        if not db_conversation:
            return None

        update_data = conversation_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_conversation, field, value)

        db_conversation.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    def delete(self, db: Session, conversation_id: UUID) -> bool:
        db_conversation = self.get_by_id(db, conversation_id)
        if not db_conversation:
            return False
        db.delete(db_conversation)
        db.commit()
        return True

    def update_timestamp(self, db: Session, conversation_id: UUID) -> None:
        db_conversation = self.get_by_id(db, conversation_id)
        if db_conversation:
            db_conversation.updated_at = datetime.now(timezone.utc)
            db.commit()

    def get_telegram_conversation(self, db: Session, user_id: UUID) -> Optional[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.telegram_chat_id.isnot(None)
        ).first()

    def get_telegram_session(self, db: Session, user_id: UUID, session_id: str) -> Optional[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.telegram_chat_id == session_id
        ).first()

    def create_telegram_session(
        self,
        db: Session,
        user_id: UUID,
        session_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        existing = self.get_telegram_session(db, user_id, session_id)
        if existing:
            return existing

        db_conversation = Conversation(
            user_id=user_id,
            title=title or f"Session {session_id[:8]}",
            telegram_chat_id=session_id
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation

    def get_all_telegram_sessions(self, db: Session, user_id: UUID) -> List[Conversation]:
        return db.query(Conversation).filter(
            Conversation.user_id == user_id,
            Conversation.telegram_chat_id.isnot(None)
        ).all()

    def get_or_create_session(
        self,
        db: Session,
        user_id: UUID,
        session_id: str,
        title: Optional[str] = None
    ) -> Conversation:
        """Get existing session or create new one."""
        existing = self.get_telegram_session(db, user_id, session_id)
        if existing:
            return existing
        return self.create_telegram_session(db, user_id, session_id, title)

    def get_token_count(self, conversation) -> int:
        """Estimate token count from conversation messages."""
        total_chars = sum(len(m.content or "") for m in conversation.messages)
        return total_chars // 4

    async def compress_conversation(
        self,
        db: Session,
        conversation_id: UUID,
        keep_last: int = 15
    ) -> Optional[str]:
        """Compress conversation - delegates to ContextService."""
        from app.services.context_service import ContextService

        conversation = self.get_by_id(db, conversation_id)
        if not conversation:
            return None

        context_service = ContextService()
        return await context_service.compress_conversation_async(db, conversation, keep_last)