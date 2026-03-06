from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    stock = Column(Numeric(15, 2), default=0)
    min_stock = Column(Numeric(15, 2), default=0)
    max_stock = Column(Numeric(15, 2), default=0)
    unit = Column(String(30), default="unidad")
    location = Column(String(100), nullable=True)  # e.g. "Estante A, Fila 3"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
