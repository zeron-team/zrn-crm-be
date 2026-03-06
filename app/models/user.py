from sqlalchemy import Column, Integer, String, Boolean, Numeric
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
