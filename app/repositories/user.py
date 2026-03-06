from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash

class UserRepository:
    def get(self, db: Session, user_id: int) -> User | None:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserCreate) -> User:
        db_obj = User(
            email=obj_in.email,
            hashed_password=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            is_active=obj_in.is_active,
            role=obj_in.role
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        update_data = obj_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
            
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> User:
        obj = db.query(User).get(id)
        db.delete(obj)
        db.commit()
        return obj

user_repository = UserRepository()
