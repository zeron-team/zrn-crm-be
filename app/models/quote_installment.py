from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class QuoteInstallment(Base):
    __tablename__ = "quote_installments"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    installment_number = Column(Integer, nullable=False)          # 1, 2, 3...
    amount = Column(Numeric(12, 2), nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String, default="pending")                   # pending, invoiced, paid
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    quote = relationship("Quote", backref="installments")
    invoice = relationship("Invoice", backref="quote_installments")
