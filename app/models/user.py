from sqlalchemy import Column, Integer, String, Boolean, Numeric, DateTime, Date, Text, func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user") # e.g. "admin", "user", "vendedor"
    commission_pct = Column(Numeric(5, 2), nullable=True, default=0)  # Default commission % for vendedor
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime, nullable=True)

    # ── Profile / Legajo ──
    avatar_url = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    mobile = Column(String, nullable=True)
    dni = Column(String, nullable=True)
    cuil = Column(String, nullable=True)
    birth_date = Column(Date, nullable=True)
    gender = Column(String, nullable=True)           # M, F, Otro
    nationality = Column(String, nullable=True)
    marital_status = Column(String, nullable=True)    # Soltero, Casado, etc.
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)             # Provincia
    zip_code = Column(String, nullable=True)
    country = Column(String, nullable=True, default="Argentina")
    emergency_contact = Column(String, nullable=True)
    emergency_phone = Column(String, nullable=True)
    blood_type = Column(String, nullable=True)        # A+, B-, O+, etc.
    bio = Column(Text, nullable=True)                 # Observaciones personales
