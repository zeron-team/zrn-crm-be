from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, Numeric, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)

    # ── Link to User ──
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True, index=True)

    # ── Legajo & Identificación ──
    legajo = Column(String, unique=True, nullable=False, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    dni = Column(String, unique=True, nullable=False, index=True)
    cuil = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String, nullable=True)          # male, female, other, prefer_not_to_say
    marital_status = Column(String, nullable=True)   # single, married, divorced, widowed
    nationality = Column(String, nullable=True, default="Argentina")
    photo_url = Column(String, nullable=True)

    # ── Contacto ──
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    # ── Datos laborales ──
    hire_date = Column(Date, nullable=True)
    termination_date = Column(Date, nullable=True)
    department = Column(String, nullable=True)       # IT, Administración, Ventas, RRHH, etc.
    position = Column(String, nullable=True)         # Cargo/puesto
    supervisor_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    contract_type = Column(String, nullable=True, default="permanent")   # permanent, temporary, freelance, internship
    billing_type = Column(String, nullable=True, default="payroll")      # payroll, monotributo, invoice
    work_schedule = Column(String, nullable=True, default="full_time")   # full_time, part_time, shift
    weekly_hours = Column(Integer, nullable=True, default=45)

    # ── Salud y beneficios ──
    obra_social = Column(String, nullable=True)
    obra_social_plan = Column(String, nullable=True)
    obra_social_number = Column(String, nullable=True)
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)

    # ── Datos bancarios ──
    bank_name = Column(String, nullable=True)
    bank_cbu = Column(String, nullable=True)
    salary = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String, nullable=True, default="ARS")

    # ── Meta ──
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    supervisor = relationship("Employee", remote_side=[id], foreign_keys=[supervisor_id])
    time_entries = relationship("TimeEntry", back_populates="employee", cascade="all, delete-orphan")
