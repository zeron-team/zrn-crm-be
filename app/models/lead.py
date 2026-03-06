from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    contact_name = Column(String)
    email = Column(String)
    phone = Column(String)
    status = Column(String, default="New") # New, Contacted, Qualified, Lost, Converted
    source = Column(String)
    website = Column(String, nullable=True)
    address = Column(String, nullable=True)
    city = Column(String, nullable=True)
    province = Column(String, nullable=True)
    country = Column(String, nullable=True, default="Argentina")
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contacts = relationship("Contact", back_populates="lead", cascade="all, delete-orphan")
    quotes = relationship("Quote", back_populates="lead")
