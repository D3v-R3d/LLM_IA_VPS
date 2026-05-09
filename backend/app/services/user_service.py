from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from uuid import UUID

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.auth import AuthService


class UserService:
    @staticmethod
    def _hash_password(password: str) -> str:
        return AuthService.hash_password(password)

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return AuthService.verify_password(password, password_hash)

    def get_by_id(self, db: Session, user_id: UUID) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def create(self, db: Session, user_data: UserCreate) -> User:
        hashed_password = self._hash_password(user_data.password)
        db_user = User(
            email=user_data.email,
            name=user_data.name,
            password_hash=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update(self, db: Session, user_id: UUID, user_data: UserUpdate) -> Optional[User]:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return None

        update_data = user_data.model_dump(exclude_unset=True)
        if "password" in update_data:
            update_data["password_hash"] = self._hash_password(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.commit()
        db.refresh(db_user)
        return db_user

    def delete(self, db: Session, user_id: UUID) -> bool:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return False
        db.delete(db_user)
        db.commit()
        return True

    def authenticate(self, db: Session, email: str, password: str) -> Optional[User]:
        db_user = self.get_by_email(db, email)
        if not db_user:
            return None
        if not self._verify_password(password, db_user.password_hash):
            return None
        return db_user

    def update_last_login(self, db: Session, user_id: UUID) -> Optional[User]:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return None
        from datetime import datetime, timezone
        db_user.last_login = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_user)
        return db_user

    def get_by_telegram_chat_id(self, db: Session, telegram_chat_id: str) -> Optional[User]:
        return db.query(User).filter(User.telegram_chat_id == telegram_chat_id).first()

    def link_telegram_chat_id(self, db: Session, link_token: str, telegram_chat_id: str) -> bool:
        db_user = db.query(User).filter(User.telegram_link_token == link_token).first()
        if not db_user:
            return False
        db_user.telegram_chat_id = telegram_chat_id
        db_user.telegram_link_token = None
        db.commit()
        return True

    def link_telegram_chat_id_by_email(self, db: Session, email: str, telegram_chat_id: str) -> bool:
        db_user = self.get_by_email(db, email)
        if not db_user:
            return False
        if db_user.telegram_chat_id:
            return False
        db_user.telegram_chat_id = telegram_chat_id
        db.commit()
        return True

    def unlink_telegram_chat_id(self, db: Session, telegram_chat_id: str) -> bool:
        db_user = self.get_by_telegram_chat_id(db, telegram_chat_id)
        if not db_user:
            return False
        db_user.telegram_chat_id = None
        db.commit()
        return True

    def update_telegram_link_token(self, db: Session, user_id: UUID, token: str) -> bool:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return False
        db_user.telegram_link_token = token
        db.commit()
        return True

    def get_preferences(self, db: Session, user_id: UUID) -> dict:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return {}
        return db_user.preferences or {}

    def set_preference(self, db: Session, user_id: UUID, key: str, value: any) -> bool:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return False
        if db_user.preferences is None:
            db_user.preferences = {}
        db_user.preferences[key] = value
        db.flush()
        db.commit()
        db.refresh(db_user)
        return True

    def set_preferences(self, db: Session, user_id: UUID, prefs_dict: dict) -> bool:
        db_user = self.get_by_id(db, user_id)
        if not db_user:
            return False
        if db_user.preferences is None:
            db_user.preferences = {}
        db_user.preferences.update(prefs_dict)
        db.flush()
        db.commit()
        return True

    def delete_preference(self, db: Session, user_id: UUID, key: str) -> bool:
        db_user = self.get_by_id(db, user_id)
        if not db_user or not db_user.preferences:
            return False
        if key in db_user.preferences:
            del db_user.preferences[key]
            db.commit()
        return True