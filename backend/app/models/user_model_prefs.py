from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.models.database import Base


class UserModelPrefs(Base):
    __tablename__ = "user_model_prefs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, default="google")
    model = Column(String(100), nullable=False, default="gemma-4-31b-it")
    is_local = Column(Boolean, nullable=False, default=True)
    current_session = Column(String(100), nullable=True, doc="Current conversation session ID")
    embedding_model = Column(String(100), nullable=True, default="nomic-embed-text")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="model_prefs")

    def __repr__(self):
        return f"<UserModelPrefs(user_id={self.user_id}, provider={self.provider}, model={self.model}, is_local={self.is_local})>"
