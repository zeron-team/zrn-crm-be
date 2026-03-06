from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database import Base


class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(Integer, primary_key=True, index=True)

    # ── Identidad ──
    company_name = Column(String, nullable=True)
    cuit = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    slogan = Column(String, nullable=True)

    # ── Contacto ──
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)

    # ── Dirección ──
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True, default="Argentina")

    # ── Horarios ──
    work_start = Column(String, nullable=True, default="09:00")       # HH:MM
    work_end = Column(String, nullable=True, default="18:00")
    support_start = Column(String, nullable=True, default="08:00")
    support_end = Column(String, nullable=True, default="20:00")
    calendar_start = Column(String, nullable=True, default="00:00")   # visible range
    calendar_end = Column(String, nullable=True, default="23:00")

    # ── Fiscal ──
    fiscal_start_month = Column(Integer, nullable=True, default=1)    # mes inicio ejercicio
    iva_condition = Column(String, nullable=True)                     # RI, Monotributo, Exento, etc.
    iibb_number = Column(String, nullable=True)                       # Nro Ingresos Brutos

    # ── Social / Legal ──
    industry = Column(String, nullable=True)
    legal_name = Column(String, nullable=True)                        # Razón social
    fantasy_name = Column(String, nullable=True)                      # Nombre de fantasía

    # ── Meta ──
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
