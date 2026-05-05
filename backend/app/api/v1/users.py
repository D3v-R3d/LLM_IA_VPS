from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.models.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserLogin
from app.services.user_service import UserService
from app.core.auth import get_current_user, AuthService

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    name: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    existing = user_service.get_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = user_service.create(db, user_data)

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email,
        name=user.name
    )


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = user_service.authenticate(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = AuthService.create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user_id=str(user.id),
        email=user.email,
        name=user.name
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user_id: UUID = Depends(get_current_user), db: Session = Depends(get_db)):
    user = user_service.get_by_id(db, current_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, current_user_id: UUID = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = user_service.get_by_id(db, user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return db_user


@router.get("", response_model=List[UserResponse])
def list_users(current_user_id: UUID = Depends(get_current_user), skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.get_all(db, skip=skip, limit=limit)


@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, user_data: UserUpdate, current_user_id: UUID = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify another user's data"
        )

    if user_data.email:
        existing = user_service.get_by_email(db, user_data.email)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    updated = user_service.update(db, user_id, user_data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: UUID, current_user_id: UUID = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete another user's account"
        )
    if not user_service.delete(db, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")