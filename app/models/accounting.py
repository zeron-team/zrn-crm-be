"""Accounting module models — periods, entries, and tax obligations for accountants."""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class AccountingPeriod(Base):
    __tablename__ = "accounting_periods"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    month = Column(Integer, nullable=False)  # 1-12
    year = Column(Integer, nullable=False)
    status = Column(String(20), default="draft")  # draft, in_review, confirmed, filed
    total_ingresos = Column(Float, default=0)
    total_egresos = Column(Float, default=0)
    total_impuestos = Column(Float, default=0)
    total_cargas_sociales = Column(Float, default=0)
    total_retenciones = Column(Float, default=0)
    total_percepciones = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Client", backref="accounting_periods")
    entries = relationship("AccountingEntry", back_populates="period", cascade="all, delete-orphan")


class AccountingEntry(Base):
    __tablename__ = "accounting_entries"

    id = Column(Integer, primary_key=True, index=True)
    period_id = Column(Integer, ForeignKey("accounting_periods.id", ondelete="CASCADE"), nullable=False)
    concept = Column(String(200), nullable=False)
    category = Column(String(50), nullable=False)  # ingreso, egreso, impuesto, carga_social, retencion, percepcion
    subcategory = Column(String(100), nullable=True)
    amount = Column(Float, default=0)
    tax_rate = Column(Float, nullable=True)
    tax_amount = Column(Float, default=0)
    reference = Column(String(200), nullable=True)
    date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    period = relationship("AccountingPeriod", back_populates="entries")


class TaxObligation(Base):
    __tablename__ = "tax_obligations"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    tax_type = Column(String(50), nullable=False)  # IVA, IIBB, Ganancias, F931, Monotributo, DDJJ_Annual
    period_month = Column(Integer, nullable=True)
    period_year = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    status = Column(String(20), default="pending")  # pending, filed, paid, overdue
    amount = Column(Float, default=0)
    filed_date = Column(Date, nullable=True)
    payment_date = Column(Date, nullable=True)
    reference_number = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    client = relationship("Client", backref="tax_obligations")
