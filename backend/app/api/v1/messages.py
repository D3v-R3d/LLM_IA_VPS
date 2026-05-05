from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.message import MessageCreate, MessageUpdate, MessageResponse
from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.core.auth import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])
message_service = MessageService()
conversation_service = ConversationService()


def verify_ownership(db: Session, conversation_id: UUID, user_id: UUID) -> None:
    """Verify user owns the conversation."""
    conversation = conversation_service.get_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if str(conversation.user_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_data: MessageCreate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_ownership(db, message_data.conversation_id, current_user_id)
    return message_service.create(db, current_user_id, message_data)


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_msg = message_service.get_by_id(db, message_id)
    if not db_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    verify_ownership(db, db_msg.conversation_id, current_user_id)
    return db_msg


@router.get("/conversation/{conversation_id}", response_model=List[MessageResponse])
def list_conversation_messages(
    conversation_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    verify_ownership(db, conversation_id, current_user_id)
    return message_service.get_by_conversation(db, conversation_id, skip=skip, limit=limit)


@router.put("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_msg = message_service.get_by_id(db, message_id)
    if not db_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    verify_ownership(db, db_msg.conversation_id, current_user_id)
    updated = message_service.update(db, message_id, message_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return updated


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db_msg = message_service.get_by_id(db, message_id)
    if not db_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    verify_ownership(db, db_msg.conversation_id, current_user_id)
    message_service.delete(db, message_id)