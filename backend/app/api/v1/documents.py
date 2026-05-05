from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.services.document_service import DocumentService
from app.core.auth import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


def verify_document_ownership(db: Session, document_id: UUID, user_id: UUID) -> None:
    """Verify user owns the document."""
    db_doc = document_service.get_by_id(db, document_id)
    if not db_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    if str(db_doc.user_id) != str(user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    document_data: DocumentCreate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return document_service.create(db, current_user_id, document_data)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_document_ownership(db, document_id, current_user_id)
    return document_service.get_by_id(db, document_id)


@router.get("/user/{user_id}", response_model=List[DocumentResponse])
def list_user_documents(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    if str(user_id) != str(current_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return document_service.get_by_user(db, user_id, skip=skip, limit=limit)


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    current_user_id: UUID = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    return document_service.get_by_user(db, current_user_id, skip=skip, limit=limit)


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(
    document_id: UUID,
    document_data: DocumentUpdate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_document_ownership(db, document_id, current_user_id)
    updated = document_service.update(db, document_id, document_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return updated


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    verify_document_ownership(db, document_id, current_user_id)
    document_service.delete(db, document_id)