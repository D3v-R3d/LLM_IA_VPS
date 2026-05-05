from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.conversation import ConversationCreate, ConversationUpdate, ConversationResponse, ConversationWithMessages
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/conversations", tags=["conversations"])
conversation_service = ConversationService()


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(conversation_data: ConversationCreate, user_id: UUID, db: Session = Depends(get_db)):
    return conversation_service.create(db, user_id, conversation_data)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    db_conv = conversation_service.get_by_id(db, conversation_id)
    if not db_conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return db_conv


@router.get("/user/{user_id}", response_model=List[ConversationResponse])
def list_user_conversations(user_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return conversation_service.get_by_user(db, user_id, skip=skip, limit=limit)


@router.get("", response_model=List[ConversationResponse])
def list_conversations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return conversation_service.get_all(db, skip=skip, limit=limit)


@router.put("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(conversation_id: UUID, conversation_data: ConversationUpdate, db: Session = Depends(get_db)):
    updated = conversation_service.update(db, conversation_id, conversation_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return updated


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conversation_id: UUID, db: Session = Depends(get_db)):
    if not conversation_service.delete(db, conversation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")