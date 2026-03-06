from sqlalchemy import Column, Integer, String, Text, Numeric, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class QuoteStatus:
    DRAFT = "Draft"
    SENT = "Sent"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

class Quote(Base):
    __tablename__ = "quotes"

    id = Column(Integer, primary_key=True, index=True)
    quote_number = Column(String, unique=True, index=True, nullable=False)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)

    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False)
    status = Column(String, default=QuoteStatus.DRAFT)
    currency = Column(String, default="ARS", nullable=False)
    
    subtotal = Column(Numeric(10, 2), default=0.0)
    tax_amount = Column(Numeric(10, 2), default=0.0)
    total_amount = Column(Numeric(10, 2), default=0.0)
    notes = Column(Text)
    file_url = Column(String, nullable=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    commission_pct = Column(Numeric(5, 2), nullable=True, default=0)  # Commission % for this quote
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="quotes")
    lead = relationship("Lead", back_populates="quotes")
    items = relationship("QuoteItem", back_populates="quote", cascade="all, delete-orphan")
