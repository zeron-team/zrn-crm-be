from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, DateTime, Numeric
from sqlalchemy.sql import func
from app.database import Base

class PaymentOrder(Base):
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False)
    date = Column(Date, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    amount = Column(Numeric(15, 2), nullable=False, default=0)
    currency = Column(String(5), default="ARS")
    payment_method = Column(String(50), default="Transferencia")
    status = Column(String(30), default="Pendiente")
    reference = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
