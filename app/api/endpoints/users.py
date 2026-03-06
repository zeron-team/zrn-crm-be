from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import user_service

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, user_in=user_in)

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.get_users(db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user(db, user_id=user_id)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    return user_service.update_user(db, user_id=user_id, user_in=user_in)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.delete_user(db, user_id=user_id)
