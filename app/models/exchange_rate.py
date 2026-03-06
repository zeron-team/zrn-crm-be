from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime
from app.database import Base
from datetime import datetime

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    currency = Column(String(5), default="USD", nullable=False)
    buy_rate = Column(Numeric(12, 4), nullable=False)
    sell_rate = Column(Numeric(12, 4), nullable=False)
    source = Column(String(50), default="manual")
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    updated_by = Column(String(100), nullable=True)
