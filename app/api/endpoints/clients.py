from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.services.client import client_service

router = APIRouter()

@router.post("/", response_model=ClientResponse)
def create_client(client_in: ClientCreate, db: Session = Depends(get_db)):
    return client_service.create_client(db, client_in=client_in)

@router.get("/", response_model=List[ClientResponse])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return client_service.get_clients(db, skip=skip, limit=limit)

@router.get("/{client_id}", response_model=ClientResponse)
def read_client(client_id: int, db: Session = Depends(get_db)):
    return client_service.get_client(db, client_id=client_id)

@router.put("/{client_id}", response_model=ClientResponse)
def update_client(client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db)):
    return client_service.update_client(db, client_id=client_id, client_in=client_in)

@router.delete("/{client_id}", response_model=ClientResponse)
def delete_client(client_id: int, db: Session = Depends(get_db)):
    return client_service.delete_client(db, client_id=client_id)
