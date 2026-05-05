from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.document import DocumentCreate, DocumentUpdate, DocumentResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
document_service = DocumentService()


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(document_data: DocumentCreate, user_id: UUID, db: Session = Depends(get_db)):
    return document_service.create(db, user_id, document_data)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, db: Session = Depends(get_db)):
    db_doc = document_service.get_by_id(db, document_id)
    if not db_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return db_doc


@router.get("/user/{user_id}", response_model=List[DocumentResponse])
def list_user_documents(user_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return document_service.get_by_user(db, user_id, skip=skip, limit=limit)


@router.get("", response_model=List[DocumentResponse])
def list_documents(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return document_service.get_all(db, skip=skip, limit=limit)


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document(document_id: UUID, document_data: DocumentUpdate, db: Session = Depends(get_db)):
    updated = document_service.update(db, document_id, document_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return updated


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, db: Session = Depends(get_db)):
    if not document_service.delete(db, document_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")