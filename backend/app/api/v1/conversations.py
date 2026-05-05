from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse
from app.services.conversation_service import ConversationService
from app.core.auth import get_current_user

router = APIRouter(prefix="/conversations", tags=["conversations"])
conversation_service = ConversationService()


def verify_ownership(db: Session, conversation_id: UUID, user_id: UUID) -> None:
    """Verify user owns the conversation."""
    conversation = conversation_service.get_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if str(conversation.user_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conversation_data: ConversationCreate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversation = conversation_service.create(
        db=db,
        user_id=current_user_id,
        conversation_data=conversation_data
    )
    return conversation


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_ownership(db, conversation_id, current_user_id)
    return conversation_service.get_by_id(db, conversation_id)


@router.get("", response_model=List[ConversationResponse])
def list_conversations(
    current_user_id: UUID = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return conversation_service.get_all(db, user_id=current_user_id, skip=skip, limit=limit)


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: UUID,
    conversation_data: ConversationUpdate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_ownership(db, conversation_id, current_user_id)
    return conversation_service.update(db, conversation_id, conversation_data)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_ownership(db, conversation_id, current_user_id)
    conversation_service.delete(db, conversation_id)