from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.contact import ContactCreate, ContactUpdate, ContactResponse
from app.services.contact import contact_service

router = APIRouter()

@router.post("/", response_model=ContactResponse)
def create_contact(contact_in: ContactCreate, db: Session = Depends(get_db)):
    return contact_service.create_contact(db, contact_in=contact_in)

@router.get("/", response_model=List[ContactResponse])
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return contact_service.get_contacts(db, skip=skip, limit=limit)

@router.get("/{contact_id}", response_model=ContactResponse)
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    return contact_service.get_contact(db, contact_id=contact_id)

@router.put("/{contact_id}", response_model=ContactResponse)
def update_contact(contact_id: int, contact_in: ContactUpdate, db: Session = Depends(get_db)):
    return contact_service.update_contact(db, contact_id=contact_id, contact_in=contact_in)

@router.delete("/{contact_id}", response_model=ContactResponse)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    return contact_service.delete_contact(db, contact_id=contact_id)
