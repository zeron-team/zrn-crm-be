from sqlalchemy import Column, Integer, String, DateTime, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class ServicePayment(Base):
    __tablename__ = "service_payments"

    id = Column(Integer, primary_key=True, index=True)
    provider_service_id = Column(Integer, ForeignKey("provider_services.id", ondelete="CASCADE"), nullable=False)
    period_month = Column(Integer, nullable=False)  # 1-12
    period_year = Column(Integer, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(5), default="USD", nullable=False)
    exchange_rate = Column(Numeric(12, 4), nullable=True)  # sell_rate from ExchangeRate table
    amount_ars = Column(Numeric(15, 2), nullable=True)     # amount * exchange_rate
    payment_date = Column(DateTime, nullable=False)
    invoice_number = Column(String, nullable=True)
    receipt_file = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)

    provider_service = relationship("ProviderService")

    __table_args__ = (
        UniqueConstraint('provider_service_id', 'period_month', 'period_year', name='uq_service_payment_period'),
    )
