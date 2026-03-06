from sqlalchemy import Column, Integer, Numeric, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description = Column(String, nullable=True)  # Custom/edited description
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0.0)
    total_price = Column(Numeric(12, 2), nullable=False, default=0.0)

    invoice = relationship("Invoice", back_populates="items")
    product = relationship("Product")
