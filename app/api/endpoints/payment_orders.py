from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.payment_order import PaymentOrder
from app.models.provider import Provider
from app.models.client import Client
from app.models.invoice import Invoice
from pydantic import BaseModel
from typing import Optional
from datetime import date
import re

router = APIRouter(prefix="/payment-orders", tags=["payment-orders"])

PREFIX = "OP"

def get_next_number(db: Session) -> str:
    last = db.query(PaymentOrder.number).order_by(PaymentOrder.id.desc()).all()
    max_num = 0
    for (num,) in last:
        m = re.search(r'(\d+)$', num or '')
        if m:
            val = int(m.group(1))
            if val > max_num:
                max_num = val
    return f"{PREFIX}-{str(max_num + 1).zfill(5)}"

class PaymentOrderCreate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    invoice_id: Optional[int] = None
    amount: float = 0
    currency: str = "ARS"
    payment_method: str = "Transferencia"
    status: str = "Pendiente"
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentOrderUpdate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    invoice_id: Optional[int] = None
    amount: float = 0
    currency: str = "ARS"
    payment_method: str = "Transferencia"
    status: str = "Pendiente"
    reference: Optional[str] = None
    notes: Optional[str] = None

def to_dict(po, provider_name=None, client_name=None, invoice_number=None):
    return {
        "id": po.id,
        "number": po.number,
        "date": str(po.date),
        "client_id": po.client_id,
        "client_name": client_name,
        "provider_id": po.provider_id,
        "provider_name": provider_name,
        "invoice_id": po.invoice_id,
        "invoice_number": invoice_number,
        "amount": float(po.amount),
        "currency": po.currency,
        "payment_method": po.payment_method,
        "status": po.status,
        "reference": po.reference,
        "notes": po.notes,
        "created_at": str(po.created_at) if po.created_at else None,
    }

def resolve(db, po):
    prov = db.query(Provider).filter(Provider.id == po.provider_id).first() if po.provider_id else None
    client = db.query(Client).filter(Client.id == po.client_id).first() if po.client_id else None
    inv = db.query(Invoice).filter(Invoice.id == po.invoice_id).first() if po.invoice_id else None
    return to_dict(po, prov.name if prov else None, client.name if client else None, inv.invoice_number if inv else None)

@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"next_number": get_next_number(db)}

@router.get("")
def list_payment_orders(db: Session = Depends(get_db)):
    orders = db.query(PaymentOrder).order_by(PaymentOrder.date.desc()).all()
    return [resolve(db, o) for o in orders]

@router.get("/{order_id}")
def get_payment_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Payment order not found")
    return resolve(db, o)

@router.post("")
def create_payment_order(data: PaymentOrderCreate, db: Session = Depends(get_db)):
    number = data.number if data.number else get_next_number(db)
    po = PaymentOrder(
        number=number, date=data.date, client_id=data.client_id,
        provider_id=data.provider_id, invoice_id=data.invoice_id,
        amount=data.amount, currency=data.currency, payment_method=data.payment_method,
        status=data.status, reference=data.reference, notes=data.notes,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return resolve(db, po)

@router.put("/{order_id}")
def update_payment_order(order_id: int, data: PaymentOrderUpdate, db: Session = Depends(get_db)):
    po = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Payment order not found")
    if data.number:
        po.number = data.number
    po.date = data.date
    po.client_id = data.client_id
    po.provider_id = data.provider_id
    po.invoice_id = data.invoice_id
    po.amount = data.amount
    po.currency = data.currency
    po.payment_method = data.payment_method
    po.status = data.status
    po.reference = data.reference
    po.notes = data.notes
    db.commit()
    db.refresh(po)
    return resolve(db, po)

@router.delete("/{order_id}")
def delete_payment_order(order_id: int, db: Session = Depends(get_db)):
    po = db.query(PaymentOrder).filter(PaymentOrder.id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Payment order not found")
    db.delete(po)
    db.commit()
    return {"ok": True}
