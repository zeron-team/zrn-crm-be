from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class InvoiceIvaItem(Base):
    __tablename__ = "invoice_iva_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    iva_id = Column(Integer, nullable=False)             # 3=0%, 4=10.5%, 5=21%, 6=27%, 8=5%, 9=2.5%
    base_imp = Column(Numeric(12, 2), nullable=False)    # Base imponible
    importe = Column(Numeric(12, 2), nullable=False)     # Monto del IVA

    invoice = relationship("Invoice", back_populates="iva_items")
