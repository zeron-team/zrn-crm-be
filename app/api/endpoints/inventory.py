from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.inventory import InventoryItem
from app.models.product import Product
from app.models.warehouse import Warehouse
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/inventory", tags=["inventory"])

class InventoryCreate(BaseModel):
    product_id: int
    warehouse_id: Optional[int] = None
    stock: float = 0
    min_stock: float = 0
    max_stock: float = 0
    unit: str = "unidad"
    location: Optional[str] = None
    notes: Optional[str] = None

class InventoryUpdate(BaseModel):
    product_id: Optional[int] = None
    warehouse_id: Optional[int] = None
    stock: Optional[float] = None
    min_stock: Optional[float] = None
    max_stock: Optional[float] = None
    unit: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class StockAdjust(BaseModel):
    quantity: float
    reason: str = ""

def to_dict(item, product=None, warehouse=None):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": product.name if product else None,
        "product_type": product.type if product else None,
        "product_category": product.category if product else None,
        "product_family": product.family if product else None,
        "product_subcategory": product.subcategory if product else None,
        "warehouse_id": item.warehouse_id,
        "warehouse_name": warehouse.name if warehouse else None,
        "warehouse_code": warehouse.code if warehouse else None,
        "stock": float(item.stock) if item.stock else 0,
        "min_stock": float(item.min_stock) if item.min_stock else 0,
        "max_stock": float(item.max_stock) if item.max_stock else 0,
        "unit": item.unit,
        "location": item.location,
        "notes": item.notes,
        "stock_status": "critical" if item.stock and item.min_stock and float(item.stock) <= float(item.min_stock) else ("warning" if item.stock and item.max_stock and float(item.max_stock) > 0 and float(item.stock) >= float(item.max_stock) else "normal"),
        "created_at": str(item.created_at) if item.created_at else None,
    }

def resolve(db, item):
    product = db.query(Product).filter(Product.id == item.product_id).first()
    warehouse = db.query(Warehouse).filter(Warehouse.id == item.warehouse_id).first() if item.warehouse_id else None
    return to_dict(item, product, warehouse)

@router.get("")
def list_inventory(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).order_by(InventoryItem.id.desc()).all()
    return [resolve(db, i) for i in items]

@router.get("/summary")
def inventory_summary(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).all()
    total = len(items)
    critical = sum(1 for i in items if i.stock is not None and i.min_stock is not None and float(i.stock) <= float(i.min_stock))
    over = sum(1 for i in items if i.stock is not None and i.max_stock is not None and float(i.max_stock) > 0 and float(i.stock) >= float(i.max_stock))
    total_value = 0
    for i in items:
        p = db.query(Product).filter(Product.id == i.product_id).first()
        if p and p.price:
            total_value += float(p.price) * float(i.stock or 0)
    return {"total_items": total, "critical_stock": critical, "over_stock": over, "total_value": round(total_value, 2)}

@router.get("/{item_id}")
def get_inventory_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return resolve(db, item)

@router.post("")
def create_inventory_item(data: InventoryCreate, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = db.query(InventoryItem).filter(InventoryItem.product_id == data.product_id, InventoryItem.warehouse_id == data.warehouse_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Product already tracked in this warehouse")
    item = InventoryItem(
        product_id=data.product_id, warehouse_id=data.warehouse_id,
        stock=data.stock, min_stock=data.min_stock, max_stock=data.max_stock,
        unit=data.unit, location=data.location, notes=data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return resolve(db, item)

@router.put("/{item_id}")
def update_inventory_item(item_id: int, data: InventoryUpdate, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    if data.product_id is not None: item.product_id = data.product_id
    if data.warehouse_id is not None: item.warehouse_id = data.warehouse_id
    if data.stock is not None: item.stock = data.stock
    if data.min_stock is not None: item.min_stock = data.min_stock
    if data.max_stock is not None: item.max_stock = data.max_stock
    if data.unit is not None: item.unit = data.unit
    if data.location is not None: item.location = data.location
    if data.notes is not None: item.notes = data.notes
    db.commit()
    db.refresh(item)
    return resolve(db, item)

@router.post("/{item_id}/adjust")
def adjust_stock(item_id: int, data: StockAdjust, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    current = float(item.stock or 0)
    new_stock = current + data.quantity
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")
    item.stock = new_stock
    db.commit()
    db.refresh(item)
    return resolve(db, item)

@router.delete("/{item_id}")
def delete_inventory_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    db.delete(item)
    db.commit()
    return {"ok": True}
