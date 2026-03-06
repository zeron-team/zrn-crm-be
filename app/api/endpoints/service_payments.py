from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import os
import shutil
from app.database import get_db
from app.models.service_payment import ServicePayment
from app.models.provider_service import ProviderService
from app.schemas.service_payment import ServicePaymentCreate, ServicePaymentUpdate, ServicePaymentResponse
from app.api.endpoints.exchange_rates import get_rate_for_date

router = APIRouter(prefix="/service-payments", tags=["service-payments"])

UPLOAD_DIR = "uploads/service_payments"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _apply_exchange_rate(db: Session, obj: ServicePayment):
    """Auto-compute exchange_rate and amount_ars from the ExchangeRate table."""
    currency = obj.currency or "USD"
    if currency == "ARS":
        obj.exchange_rate = 1
        obj.amount_ars = obj.amount
    else:
        rate = get_rate_for_date(db, obj.payment_date, currency)
        obj.exchange_rate = rate
        obj.amount_ars = round(float(obj.amount or 0) * rate, 2)


@router.get("/", response_model=List[ServicePaymentResponse])
def get_all_service_payments(db: Session = Depends(get_db)):
    return db.query(ServicePayment).all()

@router.get("/enriched")
def get_enriched_service_payments(db: Session = Depends(get_db)):
    """Return all payments with provider/service info for the purchases page."""
    from app.models.provider import Provider
    payments = db.query(ServicePayment).order_by(
        ServicePayment.period_year.desc(),
        ServicePayment.period_month.desc(),
        ServicePayment.payment_date.desc()
    ).all()
    services = db.query(ProviderService).all()
    providers = db.query(Provider).all()

    svc_map = {s.id: s for s in services}
    prov_map = {p.id: p for p in providers}

    result = []
    for p in payments:
        svc = svc_map.get(p.provider_service_id)
        prov = prov_map.get(svc.provider_id) if svc else None
        result.append({
            "id": p.id,
            "provider_service_id": p.provider_service_id,
            "provider_name": prov.name if prov else "—",
            "provider_id": prov.id if prov else None,
            "service_name": svc.name or (svc.product_name if hasattr(svc, 'product_name') else None) or "Servicio",
            "service_currency": svc.currency if svc else "USD",
            "service_cost": float(svc.cost_price or 0) if svc else 0,
            "period_month": p.period_month,
            "period_year": p.period_year,
            "amount": float(p.amount or 0),
            "currency": p.currency or "USD",
            "exchange_rate": float(p.exchange_rate or 1),
            "amount_ars": float(p.amount_ars or 0),
            "payment_date": str(p.payment_date) if p.payment_date else None,
            "invoice_number": p.invoice_number,
            "receipt_file": p.receipt_file,
            "created_at": str(p.created_at) if p.created_at else None,
            "created_by": p.created_by,
            "updated_at": str(p.updated_at) if p.updated_at else None,
            "updated_by": p.updated_by,
        })

    # Also return providers and services for the create form
    providers_list = [{"id": p.id, "name": p.name} for p in providers if p.is_active]
    services_list = [{
        "id": s.id, "provider_id": s.provider_id,
        "name": s.name or "Servicio", "cost_price": float(s.cost_price or 0),
        "currency": s.currency, "billing_cycle": s.billing_cycle, "status": s.status,
    } for s in services if s.status == "Active"]

    return {"payments": result, "providers": providers_list, "services": services_list}

@router.get("/service/{service_id}", response_model=List[ServicePaymentResponse])
def get_payments_for_service(service_id: int, db: Session = Depends(get_db)):
    return db.query(ServicePayment).filter(
        ServicePayment.provider_service_id == service_id
    ).order_by(ServicePayment.period_year.desc(), ServicePayment.period_month.desc()).all()

@router.post("/", response_model=ServicePaymentResponse)
def create_service_payment(payload: ServicePaymentCreate, db: Session = Depends(get_db)):
    # Inherit currency from the provider service if not specified
    svc = db.query(ProviderService).filter(ProviderService.id == payload.provider_service_id).first()
    currency = payload.currency or (svc.currency if svc else "USD")

    # Check for existing payment in same period
    existing = db.query(ServicePayment).filter(
        ServicePayment.provider_service_id == payload.provider_service_id,
        ServicePayment.period_month == payload.period_month,
        ServicePayment.period_year == payload.period_year,
    ).first()
    if existing:
        existing.amount = payload.amount
        existing.payment_date = payload.payment_date
        existing.invoice_number = payload.invoice_number
        existing.currency = currency
        existing.updated_by = payload.created_by
        _apply_exchange_rate(db, existing)
        db.commit()
        db.refresh(existing)
        return existing
    
    data = payload.model_dump()
    data["currency"] = currency
    db_obj = ServicePayment(**data)
    _apply_exchange_rate(db, db_obj)
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/{payment_id}", response_model=ServicePaymentResponse)
def update_service_payment(payment_id: int, payload: ServicePaymentUpdate, db: Session = Depends(get_db)):
    obj = db.query(ServicePayment).filter(ServicePayment.id == payment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    
    # Recalculate ARS amount
    _apply_exchange_rate(db, obj)
    
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{payment_id}/upload", response_model=ServicePaymentResponse)
def upload_receipt(payment_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    obj = db.query(ServicePayment).filter(ServicePayment.id == payment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    ext = os.path.splitext(file.filename)[1] if file.filename else ".pdf"
    filename = f"receipt_{payment_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    obj.receipt_file = f"/{UPLOAD_DIR}/{filename}"
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/{payment_id}", response_model=ServicePaymentResponse)
def delete_service_payment(payment_id: int, db: Session = Depends(get_db)):
    obj = db.query(ServicePayment).filter(ServicePayment.id == payment_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Payment not found")
    if obj.receipt_file:
        filepath = obj.receipt_file.lstrip("/")
        if os.path.exists(filepath):
            os.remove(filepath)
    db.delete(obj)
    db.commit()
    return obj
