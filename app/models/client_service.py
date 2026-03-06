from sqlalchemy import Column, Integer, String, Date, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class ClientService(Base):
    __tablename__ = "client_services"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    name = Column(String, index=True, nullable=False)
    status = Column(String, default="Active")
    currency = Column(String, default="ARS", nullable=False)
    billing_cycle = Column(String, default="Monthly")
    characteristics = Column(JSON, default={})
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)

    client = relationship("Client", back_populates="services")
    product = relationship("Product")
