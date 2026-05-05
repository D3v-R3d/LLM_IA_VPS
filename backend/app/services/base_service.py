"""
Base Service Module

Provides common CRUD operations for all services.
"""

from typing import TypeVar, Generic, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import inspect

Model = TypeVar("Model")


class BaseService(Generic[Model]):
    """Base service class with common CRUD operations."""

    def __init__(self, model: type[Model]):
        self.model = model

    def get_by_id(self, db: Session, id: UUID) -> Optional[Model]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[Model]:
        return db.query(self.model).offset(skip).limit(limit).all()

    def update(self, db: Session, id: UUID, update_data: dict) -> Optional[Model]:
        db_obj = self.get_by_id(db, id)
        if not db_obj:
            return None

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        if hasattr(db_obj, "updated_at"):
            db_obj.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: UUID) -> bool:
        db_obj = self.get_by_id(db, id)
        if not db_obj:
            return False
        db.delete(db_obj)
        db.commit()
        return True