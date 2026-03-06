from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime


class InvoiceAuditLog(Base):
    __tablename__ = "invoice_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    action = Column(String(50), nullable=False)  # created, status_changed, arca_emitted, nc_associated, deleted, edited
    description = Column(Text, nullable=True)
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    user_name = Column(String(100), nullable=True, default="Sistema")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    invoice = relationship("Invoice", backref="audit_logs")
