from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base

class DeliveryNote(Base):
    __tablename__ = "delivery_notes"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False)
    date = Column(Date, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    status = Column(String(30), default="Pendiente")
    items = Column(JSON, default=[])
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
