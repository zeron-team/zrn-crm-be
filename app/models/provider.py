from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    cuit_dni = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    address = Column(String)
    is_active = Column(Boolean, default=True)

    contacts = relationship("Contact", back_populates="provider")
    services = relationship("ProviderService", back_populates="provider", cascade="all, delete-orphan")
    invoices = relationship("Invoice", back_populates="provider")
