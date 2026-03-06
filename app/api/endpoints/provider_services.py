from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models.provider_service import ProviderService
from app.schemas.provider_service import ProviderServiceCreate, ProviderServiceUpdate, ProviderServiceResponse

router = APIRouter()


def _enrich(service: ProviderService) -> dict:
    """Build response dict with product info."""
    data = {
        "id": service.id,
        "provider_id": service.provider_id,
        "product_id": service.product_id,
        "name": service.name,
        "cost_price": float(service.cost_price),
        "currency": service.currency,
        "billing_cycle": service.billing_cycle,
        "expiration_date": service.expiration_date,
        "notify_days_before": service.notify_days_before,
        "status": service.status,
        "product_name": None,
        "product_family": None,
        "product_category": None,
        "product_subcategory": None,
    }
    if service.product:
        data["product_name"] = service.product.name
        data["product_family"] = service.product.family
        data["product_category"] = service.product.category
        data["product_subcategory"] = service.product.subcategory
    return data


def _query(db: Session):
    return db.query(ProviderService).options(
        joinedload(ProviderService.product)
    )


@router.post("/", response_model=ProviderServiceResponse)
def create_provider_service(service: ProviderServiceCreate, db: Session = Depends(get_db)):
    db_service = ProviderService(**service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    db_service = _query(db).filter(ProviderService.id == db_service.id).first()
    return _enrich(db_service)

@router.get("/", response_model=List[ProviderServiceResponse])
def get_provider_services(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    services = _query(db).offset(skip).limit(limit).all()
    return [_enrich(s) for s in services]

@router.get("/provider/{provider_id}", response_model=List[ProviderServiceResponse])
def get_services_by_provider(provider_id: int, db: Session = Depends(get_db)):
    services = _query(db).filter(ProviderService.provider_id == provider_id).all()
    return [_enrich(s) for s in services]

@router.get("/{service_id}", response_model=ProviderServiceResponse)
def get_provider_service_by_id(service_id: int, db: Session = Depends(get_db)):
    service = _query(db).filter(ProviderService.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Provider Service not found")
    return _enrich(service)

@router.put("/{service_id}", response_model=ProviderServiceResponse)
def update_provider_service(service_id: int, service_update: ProviderServiceUpdate, db: Session = Depends(get_db)):
    db_service = db.query(ProviderService).filter(ProviderService.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Provider Service not found")
    
    update_data = service_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_service, key, value)
        
    db.commit()
    db.refresh(db_service)
    db_service = _query(db).filter(ProviderService.id == db_service.id).first()
    return _enrich(db_service)

@router.delete("/{service_id}")
def delete_provider_service(service_id: int, db: Session = Depends(get_db)):
    db_service = db.query(ProviderService).filter(ProviderService.id == service_id).first()
    if not db_service:
        raise HTTPException(status_code=404, detail="Provider Service not found")
        
    db.delete(db_service)
    db.commit()
    return {"message": "Service deleted successfully"}
