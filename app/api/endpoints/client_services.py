from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.client_service import ClientServiceCreate, ClientServiceResponse, ClientServiceUpdate
from app.services.client_service import client_service_service

router = APIRouter()

@router.post("/", response_model=ClientServiceResponse)
def create_service(service_in: ClientServiceCreate, db: Session = Depends(get_db)):
    return client_service_service.create_service(db, service_in=service_in)

@router.get("/", response_model=List[ClientServiceResponse])
def read_all_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return client_service_service.get_all_services(db, skip=skip, limit=limit)

@router.get("/client/{client_id}", response_model=List[ClientServiceResponse])
def read_client_services(client_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return client_service_service.get_services_by_client(db, client_id=client_id, skip=skip, limit=limit)

@router.get("/{service_id}", response_model=ClientServiceResponse)
def read_service(service_id: int, db: Session = Depends(get_db)):
    return client_service_service.get_service(db, service_id=service_id)

@router.put("/{service_id}", response_model=ClientServiceResponse)
def update_service(service_id: int, service_in: ClientServiceUpdate, db: Session = Depends(get_db)):
    return client_service_service.update_service(db, service_id=service_id, service_in=service_in)

@router.delete("/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    return client_service_service.delete_service(db, service_id=service_id)
