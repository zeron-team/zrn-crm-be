from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)          # Razón Social
    trade_name = Column(String, nullable=True, index=True)     # Nombre Comercial
    tax_condition = Column(String, nullable=True)              # Condición de IVA
    cuit_dni = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    phone = Column(String)
    address = Column(String)                                   # Dirección
    city = Column(String, nullable=True)                       # Localidad
    province = Column(String, nullable=True)                   # Provincia
    country = Column(String, nullable=True, default="Argentina")  # País
    website = Column(String, nullable=True)                      # Sitio Web
    activity = Column(String, nullable=True)                     # Actividad principal (from AFIP)
    arca_validated = Column(Boolean, default=False)               # Validated via ARCA/AFIP
    arca_validated_at = Column(DateTime, nullable=True)           # When validated
    is_active = Column(Boolean, default=True)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    contacts = relationship("Contact", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")
    services = relationship("ClientService", back_populates="client", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="client")
