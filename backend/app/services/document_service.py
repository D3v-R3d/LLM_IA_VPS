from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.models.document import Document
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentService:
    def get_by_id(self, db: Session, document_id: UUID) -> Optional[Document]:
        return db.query(Document).filter(Document.id == document_id).first()

    def get_by_user(self, db: Session, user_id: UUID, skip: int = 0, limit: int = 100) -> List[Document]:
        return db.query(Document).filter(
            Document.user_id == user_id
        ).order_by(Document.created_at.desc()).offset(skip).limit(limit).all()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Document]:
        return db.query(Document).offset(skip).limit(limit).all()

    def create(self, db: Session, user_id: UUID, document_data: DocumentCreate) -> Document:
        db_document = Document(
            user_id=user_id,
            name=document_data.name,
            content_raw=document_data.content_raw,
            type=document_data.type
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return db_document

    def update(self, db: Session, document_id: UUID, document_data: DocumentUpdate) -> Optional[Document]:
        db_document = self.get_by_id(db, document_id)
        if not db_document:
            return None

        update_data = document_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_document, field, value)

        db.commit()
        db.refresh(db_document)
        return db_document

    def delete(self, db: Session, document_id: UUID) -> bool:
        db_document = self.get_by_id(db, document_id)
        if not db_document:
            return False
        db.delete(db_document)
        db.commit()
        return True

    def get_user_document_count(self, db: Session, user_id: UUID) -> int:
        return db.query(Document).filter(Document.user_id == user_id).count()

    def mark_as_embedded(self, db: Session, document_id: UUID) -> Optional[Document]:
        db_document = self.get_by_id(db, document_id)
        if not db_document:
            return None
        db_document.is_embedded = True
        db.commit()
        db.refresh(db_document)
        return db_document

    def get_unembedded_by_user(self, db: Session, user_id: UUID) -> List[Document]:
        return db.query(Document).filter(
            Document.user_id == user_id,
            Document.is_embedded == False
        ).order_by(Document.created_at.desc()).all()