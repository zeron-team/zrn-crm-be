from sqlalchemy import Column, Integer, String, Numeric, Boolean
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String)
    price = Column(Numeric(10, 2), default=0.0)
    currency = Column(String, default="ARS", nullable=False)
    type = Column(String, default="product") # "product", "service", or "manpower"
    category = Column(String, nullable=True) # e.g. "Software", "Hardware", "Consulting"
    family = Column(String, nullable=True)   # e.g. "Development", "Infrastructure", "Support"
    subcategory = Column(String, nullable=True) # e.g. "Frontend", "Backend", "DevOps"
    is_active = Column(Boolean, default=True)

