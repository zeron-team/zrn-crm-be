from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.purchase_order import PurchaseOrder
from app.models.provider import Provider
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.user import User
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date
import re

router = APIRouter(prefix="/purchase-orders", tags=["purchase-orders"])

PREFIX = "OC"

def get_next_number(db: Session) -> str:
    last = db.query(PurchaseOrder.number).order_by(PurchaseOrder.id.desc()).all()
    max_num = 0
    for (num,) in last:
        m = re.search(r'(\d+)$', num or '')
        if m:
            val = int(m.group(1))
            if val > max_num:
                max_num = val
    return f"{PREFIX}-{str(max_num + 1).zfill(5)}"

class PurchaseOrderCreate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    invoice_id: Optional[int] = None
    seller_id: Optional[int] = None
    total_amount: float = 0
    currency: str = "ARS"
    status: str = "Borrador"
    delivery_date: Optional[date] = None
    items: List[Any] = []
    notes: Optional[str] = None

class PurchaseOrderUpdate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    invoice_id: Optional[int] = None
    seller_id: Optional[int] = None
    total_amount: float = 0
    currency: str = "ARS"
    status: str = "Borrador"
    delivery_date: Optional[date] = None
    items: List[Any] = []
    notes: Optional[str] = None

def to_dict(po, provider_name=None, client_name=None, invoice_number=None, seller_name=None):
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
        "seller_id": po.seller_id,
        "seller_name": seller_name,
        "total_amount": float(po.total_amount),
        "currency": po.currency,
        "status": po.status,
        "delivery_date": str(po.delivery_date) if po.delivery_date else None,
        "items": po.items or [],
        "notes": po.notes,
        "created_at": str(po.created_at) if po.created_at else None,
    }

def resolve(db, po):
    prov = db.query(Provider).filter(Provider.id == po.provider_id).first() if po.provider_id else None
    client = db.query(Client).filter(Client.id == po.client_id).first() if po.client_id else None
    inv = db.query(Invoice).filter(Invoice.id == po.invoice_id).first() if po.invoice_id else None
    seller = db.query(User).filter(User.id == po.seller_id).first() if po.seller_id else None
    return to_dict(po, prov.name if prov else None, client.name if client else None, inv.invoice_number if inv else None, seller.full_name if seller else None)

@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"next_number": get_next_number(db)}

@router.get("")
def list_purchase_orders(db: Session = Depends(get_db)):
    orders = db.query(PurchaseOrder).order_by(PurchaseOrder.date.desc()).all()
    return [resolve(db, o) for o in orders]

@router.get("/{order_id}")
def get_purchase_order(order_id: int, db: Session = Depends(get_db)):
    o = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return resolve(db, o)

@router.post("")
def create_purchase_order(data: PurchaseOrderCreate, db: Session = Depends(get_db)):
    number = data.number if data.number else get_next_number(db)
    po = PurchaseOrder(
        number=number, date=data.date, client_id=data.client_id,
        provider_id=data.provider_id, invoice_id=data.invoice_id,
        seller_id=data.seller_id,
        total_amount=data.total_amount, currency=data.currency, status=data.status,
        delivery_date=data.delivery_date, items=data.items, notes=data.notes,
    )
    db.add(po)
    db.commit()
    db.refresh(po)
    return resolve(db, po)

@router.put("/{order_id}")
def update_purchase_order(order_id: int, data: PurchaseOrderUpdate, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if data.number:
        po.number = data.number
    po.date = data.date
    po.client_id = data.client_id
    po.provider_id = data.provider_id
    po.invoice_id = data.invoice_id
    po.seller_id = data.seller_id
    po.total_amount = data.total_amount
    po.currency = data.currency
    po.status = data.status
    po.delivery_date = data.delivery_date
    po.items = data.items
    po.notes = data.notes
    db.commit()
    db.refresh(po)
    return resolve(db, po)

@router.delete("/{order_id}")
def delete_purchase_order(order_id: int, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    db.delete(po)
    db.commit()
    return {"ok": True}
