from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base

class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(150), nullable=False)
    address = Column(String(300), nullable=True)
    city = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(150), nullable=True)
    manager_id = Column(Integer, ForeignKey("contacts.id"), nullable=True)
    capacity = Column(String(100), nullable=True)
    warehouse_type = Column(String(50), default="General")
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
