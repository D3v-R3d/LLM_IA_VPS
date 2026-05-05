from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.message import MessageCreate, MessageUpdate, MessageResponse
from app.services.message_service import MessageService

router = APIRouter(prefix="/messages", tags=["messages"])
message_service = MessageService()


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(message_data: MessageCreate, user_id: UUID, db: Session = Depends(get_db)):
    return message_service.create(db, user_id, message_data)


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(message_id: UUID, db: Session = Depends(get_db)):
    db_msg = message_service.get_by_id(db, message_id)
    if not db_msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return db_msg


@router.get("/conversation/{conversation_id}", response_model=List[MessageResponse])
def list_conversation_messages(
    conversation_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return message_service.get_by_conversation(db, conversation_id, skip=skip, limit=limit)


@router.get("/user/{user_id}", response_model=List[MessageResponse])
def list_user_messages(user_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return message_service.get_by_user(db, user_id, skip=skip, limit=limit)


@router.put("/{message_id}", response_model=MessageResponse)
def update_message(message_id: UUID, message_data: MessageUpdate, db: Session = Depends(get_db)):
    updated = message_service.update(db, message_id, message_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return updated


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(message_id: UUID, db: Session = Depends(get_db)):
    if not message_service.delete(db, message_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")