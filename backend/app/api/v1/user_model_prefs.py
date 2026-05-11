"""
User Model Preferences API

Endpoints for managing user LLM model preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.database import get_db
from app.core.auth import get_current_user
from app.services.user_service import UserService
from app.models.user_model_prefs import UserModelPrefs

router = APIRouter(prefix="/users/{user_id}/model-prefs", tags=["user_model_prefs"])
user_service = UserService()


class ModelPrefsCreate(BaseModel):
    provider: str = "ollama"
    model: str = "gemma4:31b"
    is_local: bool = True
    embedding_model: Optional[str] = "nomic-embed-text"


class ModelPrefsResponse(BaseModel):
    provider: str
    model: str
    is_local: bool
    embedding_model: Optional[str]


@router.get("", response_model=ModelPrefsResponse)
def get_model_prefs(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another user's preferences")

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    prefs = user.model_prefs
    if not prefs:
        return ModelPrefsResponse(
            provider="ollama",
            model="gemma4:31b",
            is_local=True,
            embedding_model="nomic-embed-text"
        )

    return ModelPrefsResponse(
        provider=prefs.provider,
        model=prefs.model,
        is_local=prefs.is_local,
        embedding_model=prefs.embedding_model
    )


@router.put("", response_model=ModelPrefsResponse)
def upsert_model_prefs(
    user_id: UUID,
    prefs_data: ModelPrefsCreate,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another user's preferences")

    user = user_service.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.model_prefs:
        prefs = user.model_prefs
        prefs.provider = prefs_data.provider
        prefs.model = prefs_data.model
        prefs.is_local = prefs_data.is_local
        prefs.embedding_model = prefs_data.embedding_model
    else:
        prefs = UserModelPrefs(
            user_id=user_id,
            provider=prefs_data.provider,
            model=prefs_data.model,
            is_local=prefs_data.is_local,
            embedding_model=prefs_data.embedding_model
        )
        db.add(prefs)

    db.commit()
    db.refresh(prefs)

    return ModelPrefsResponse(
        provider=prefs.provider,
        model=prefs.model,
        is_local=prefs.is_local,
        embedding_model=prefs.embedding_model
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_model_prefs(
    user_id: UUID,
    current_user_id: UUID = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete another user's preferences")

    user = user_service.get_by_id(db, user_id)
    if not user or not user.model_prefs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model preferences not found")

    db.delete(user.model_prefs)
    db.commit()
