from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.models.message import Message, MessageRole
from app.schemas.message import MessageCreate, MessageUpdate


class MessageService:
    def get_by_id(self, db: Session, message_id: UUID) -> Optional[Message]:
        return db.query(Message).filter(Message.id == message_id).first()

    def get_by_conversation(
        self, db: Session, conversation_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        return db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).offset(skip).limit(limit).all()

    def get_by_user(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Message]:
        return db.query(Message).filter(
            Message.user_id == user_id
        ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, user_id: UUID, message_data: MessageCreate) -> Message:
        db_message = Message(
            user_id=user_id,
            conversation_id=message_data.conversation_id,
            role=message_data.role.value,
            content=message_data.content
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message

    def update(self, db: Session, message_id: UUID, message_data: MessageUpdate) -> Optional[Message]:
        db_message = self.get_by_id(db, message_id)
        if not db_message:
            return None

        update_data = message_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_message, field, value)

        db.commit()
        db.refresh(db_message)
        return db_message

    def delete(self, db: Session, message_id: UUID) -> bool:
        db_message = self.get_by_id(db, message_id)
        if not db_message:
            return False
        db.delete(db_message)
        db.commit()
        return True

    def get_conversation_message_count(self, db: Session, conversation_id: UUID) -> int:
        return db.query(Message).filter(Message.conversation_id == conversation_id).count()