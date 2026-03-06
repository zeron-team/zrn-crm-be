from sqlalchemy.orm import Session
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactUpdate

class ContactRepository:
    def get(self, db: Session, id: int) -> Contact | None:
        return db.query(Contact).filter(Contact.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Contact]:
        return db.query(Contact).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ContactCreate) -> Contact:
        db_obj = Contact(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Contact, obj_in: ContactUpdate) -> Contact:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Contact:
        obj = db.query(Contact).get(id)
        db.delete(obj)
        db.commit()
        return obj

contact_repository = ContactRepository()
