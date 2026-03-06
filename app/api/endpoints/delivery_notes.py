from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc
from app.database import get_db
from app.models.delivery_note import DeliveryNote
from app.models.client import Client
from app.models.invoice import Invoice
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date
import re

router = APIRouter(prefix="/delivery-notes", tags=["delivery-notes"])

PREFIX = "R"

def get_next_number(db: Session) -> str:
    last = db.query(DeliveryNote.number).order_by(DeliveryNote.id.desc()).all()
    max_num = 0
    for (num,) in last:
        m = re.search(r'(\d+)$', num or '')
        if m:
            val = int(m.group(1))
            if val > max_num:
                max_num = val
    return f"{PREFIX}-{str(max_num + 1).zfill(5)}"

class DeliveryNoteCreate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    invoice_id: Optional[int] = None
    status: str = "Pendiente"
    items: List[Any] = []
    notes: Optional[str] = None

class DeliveryNoteUpdate(BaseModel):
    number: Optional[str] = None
    date: date
    client_id: Optional[int] = None
    invoice_id: Optional[int] = None
    status: str = "Pendiente"
    items: List[Any] = []
    notes: Optional[str] = None

def to_dict(dn, client_name=None, invoice_number=None):
    return {
        "id": dn.id,
        "number": dn.number,
        "date": str(dn.date),
        "client_id": dn.client_id,
        "client_name": client_name,
        "invoice_id": dn.invoice_id,
        "invoice_number": invoice_number,
        "status": dn.status,
        "items": dn.items or [],
        "notes": dn.notes,
        "created_at": str(dn.created_at) if dn.created_at else None,
    }

def resolve(db, dn):
    client = db.query(Client).filter(Client.id == dn.client_id).first() if dn.client_id else None
    inv = db.query(Invoice).filter(Invoice.id == dn.invoice_id).first() if dn.invoice_id else None
    return to_dict(dn, client.name if client else None, inv.invoice_number if inv else None)

@router.get("/next-number")
def next_number(db: Session = Depends(get_db)):
    return {"next_number": get_next_number(db)}

@router.get("")
def list_delivery_notes(db: Session = Depends(get_db)):
    notes = db.query(DeliveryNote).order_by(DeliveryNote.date.desc()).all()
    return [resolve(db, n) for n in notes]

@router.get("/{note_id}")
def get_delivery_note(note_id: int, db: Session = Depends(get_db)):
    n = db.query(DeliveryNote).filter(DeliveryNote.id == note_id).first()
    if not n:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    return resolve(db, n)

@router.post("")
def create_delivery_note(data: DeliveryNoteCreate, db: Session = Depends(get_db)):
    number = data.number if data.number else get_next_number(db)
    dn = DeliveryNote(
        number=number, date=data.date, client_id=data.client_id,
        invoice_id=data.invoice_id, status=data.status,
        items=data.items, notes=data.notes,
    )
    db.add(dn)
    db.commit()
    db.refresh(dn)
    return resolve(db, dn)

@router.put("/{note_id}")
def update_delivery_note(note_id: int, data: DeliveryNoteUpdate, db: Session = Depends(get_db)):
    dn = db.query(DeliveryNote).filter(DeliveryNote.id == note_id).first()
    if not dn:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    if data.number:
        dn.number = data.number
    dn.date = data.date
    dn.client_id = data.client_id
    dn.invoice_id = data.invoice_id
    dn.status = data.status
    dn.items = data.items
    dn.notes = data.notes
    db.commit()
    db.refresh(dn)
    return resolve(db, dn)

@router.delete("/{note_id}")
def delete_delivery_note(note_id: int, db: Session = Depends(get_db)):
    dn = db.query(DeliveryNote).filter(DeliveryNote.id == note_id).first()
    if not dn:
        raise HTTPException(status_code=404, detail="Delivery note not found")
    db.delete(dn)
    db.commit()
    return {"ok": True}
