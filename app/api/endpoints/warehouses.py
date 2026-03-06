from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.warehouse import Warehouse
from app.models.contact import Contact
from pydantic import BaseModel
from typing import Optional
import re

router = APIRouter(prefix="/warehouses", tags=["warehouses"])

PREFIX = "DEP"

def get_next_code(db: Session) -> str:
    last = db.query(Warehouse.code).order_by(Warehouse.id.desc()).all()
    max_num = 0
    for (code,) in last:
        m = re.search(r'(\d+)$', code or '')
        if m:
            val = int(m.group(1))
            if val > max_num:
                max_num = val
    return f"{PREFIX}-{str(max_num + 1).zfill(3)}"

class WarehouseCreate(BaseModel):
    code: Optional[str] = None
    name: str
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_id: Optional[int] = None
    capacity: Optional[str] = None
    warehouse_type: str = "General"
    is_active: bool = True
    notes: Optional[str] = None

class WarehouseUpdate(WarehouseCreate):
    pass

def to_dict(w, contact=None):
    return {
        "id": w.id,
        "code": w.code,
        "name": w.name,
        "address": w.address,
        "city": w.city,
        "province": w.province,
        "zip_code": w.zip_code,
        "phone": w.phone,
        "email": w.email,
        "manager_id": w.manager_id,
        "manager_name": contact.name if contact else None,
        "manager_phone": contact.phone if contact else None,
        "manager_email": contact.email if contact else None,
        "capacity": w.capacity,
        "warehouse_type": w.warehouse_type,
        "is_active": w.is_active,
        "notes": w.notes,
        "created_at": str(w.created_at) if w.created_at else None,
    }

def resolve(db, w):
    contact = db.query(Contact).filter(Contact.id == w.manager_id).first() if w.manager_id else None
    return to_dict(w, contact)

@router.get("/next-code")
def next_code(db: Session = Depends(get_db)):
    return {"next_code": get_next_code(db)}

@router.get("")
def list_warehouses(db: Session = Depends(get_db)):
    items = db.query(Warehouse).order_by(Warehouse.name).all()
    return [resolve(db, w) for w in items]

@router.get("/{wh_id}")
def get_warehouse(wh_id: int, db: Session = Depends(get_db)):
    w = db.query(Warehouse).filter(Warehouse.id == wh_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    return resolve(db, w)

@router.post("")
def create_warehouse(data: WarehouseCreate, db: Session = Depends(get_db)):
    code = data.code if data.code else get_next_code(db)
    w = Warehouse(
        code=code, name=data.name, address=data.address, city=data.city,
        province=data.province, zip_code=data.zip_code, phone=data.phone,
        email=data.email, manager_id=data.manager_id, capacity=data.capacity,
        warehouse_type=data.warehouse_type, is_active=data.is_active, notes=data.notes,
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return resolve(db, w)

@router.put("/{wh_id}")
def update_warehouse(wh_id: int, data: WarehouseUpdate, db: Session = Depends(get_db)):
    w = db.query(Warehouse).filter(Warehouse.id == wh_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if data.code: w.code = data.code
    w.name = data.name
    w.address = data.address
    w.city = data.city
    w.province = data.province
    w.zip_code = data.zip_code
    w.phone = data.phone
    w.email = data.email
    w.manager_id = data.manager_id
    w.capacity = data.capacity
    w.warehouse_type = data.warehouse_type
    w.is_active = data.is_active
    w.notes = data.notes
    db.commit()
    db.refresh(w)
    return resolve(db, w)

@router.delete("/{wh_id}")
def delete_warehouse(wh_id: int, db: Session = Depends(get_db)):
    w = db.query(Warehouse).filter(Warehouse.id == wh_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    db.delete(w)
    db.commit()
    return {"ok": True}
