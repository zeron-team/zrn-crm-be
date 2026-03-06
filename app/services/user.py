from sqlalchemy.orm import Session
from app.repositories.user import user_repository
from app.schemas.user import UserCreate, UserUpdate
from fastapi import HTTPException, status

class UserService:
    def create_user(self, db: Session, user_in: UserCreate):
        user = user_repository.get_by_email(db, email=user_in.email)
        if user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )
        return user_repository.create(db, obj_in=user_in)

    def get_user(self, db: Session, user_id: int):
        user = user_repository.get(db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user
        
    def get_users(self, db: Session, skip: int = 0, limit: int = 100):
        return user_repository.get_multi(db, skip=skip, limit=limit)

    def update_user(self, db: Session, user_id: int, user_in: UserUpdate):
        user = user_repository.get(db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user_repository.update(db, db_obj=user, obj_in=user_in)

    def delete_user(self, db: Session, user_id: int):
        user = user_repository.get(db, user_id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        return user_repository.remove(db, id=user_id)

user_service = UserService()
