from sqlalchemy import Column, Integer, String, ForeignKey, Date, Numeric
from sqlalchemy.orm import relationship
from app.database import Base

class ProviderService(Base):
    __tablename__ = "provider_services"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    name = Column(String, nullable=True)  # optional alias / description
    cost_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="USD", nullable=False)
    billing_cycle = Column(String, default="Monthly", nullable=False)
    expiration_date = Column(Date, nullable=False)
    notify_days_before = Column(Integer, default=3, nullable=False)
    status = Column(String, default="Active", nullable=False)

    provider = relationship("Provider", back_populates="services")
    product = relationship("Product", lazy="joined")
