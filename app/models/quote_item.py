from sqlalchemy import Column, Integer, String, Text, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class QuoteItem(Base):
    __tablename__ = "quote_items"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    
    description = Column(String, nullable=False)
    quantity = Column(Numeric(10, 2), default=1.0, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(10, 2), nullable=False)

    quote = relationship("Quote", back_populates="items")
    product = relationship("Product")
