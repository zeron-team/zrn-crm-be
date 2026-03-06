from sqlalchemy.orm import Session
from app.repositories.contact import contact_repository
from app.schemas.contact import ContactCreate, ContactUpdate
from fastapi import HTTPException, status

class ContactService:
    def create_contact(self, db: Session, contact_in: ContactCreate):
        return contact_repository.create(db, obj_in=contact_in)

    def get_contact(self, db: Session, contact_id: int):
        contact = contact_repository.get(db, id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
        
    def get_contacts(self, db: Session, skip: int = 0, limit: int = 100):
        return contact_repository.get_multi(db, skip=skip, limit=limit)

    def update_contact(self, db: Session, contact_id: int, contact_in: ContactUpdate):
        contact = contact_repository.get(db, id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact_repository.update(db, db_obj=contact, obj_in=contact_in)

    def delete_contact(self, db: Session, contact_id: int):
        contact = contact_repository.get(db, id=contact_id)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact_repository.remove(db, id=contact_id)

contact_service = ContactService()
