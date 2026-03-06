from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.provider import ProviderCreate, ProviderUpdate, ProviderResponse
from app.services.provider import provider_service

router = APIRouter()

@router.post("/", response_model=ProviderResponse)
def create_provider(provider_in: ProviderCreate, db: Session = Depends(get_db)):
    return provider_service.create_provider(db, provider_in=provider_in)

@router.get("/", response_model=List[ProviderResponse])
def read_providers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return provider_service.get_providers(db, skip=skip, limit=limit)

@router.get("/{provider_id}", response_model=ProviderResponse)
def read_provider(provider_id: int, db: Session = Depends(get_db)):
    return provider_service.get_provider(db, provider_id=provider_id)

@router.put("/{provider_id}", response_model=ProviderResponse)
def update_provider(provider_id: int, provider_in: ProviderUpdate, db: Session = Depends(get_db)):
    return provider_service.update_provider(db, provider_id=provider_id, provider_in=provider_in)

@router.delete("/{provider_id}", response_model=ProviderResponse)
def delete_provider(provider_id: int, db: Session = Depends(get_db)):
    return provider_service.delete_provider(db, provider_id=provider_id)
