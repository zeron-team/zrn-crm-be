from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, index=True)
    phone = Column(String)
    position = Column(String)
    
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)

    client = relationship("Client", back_populates="contacts")
    provider = relationship("Provider", back_populates="contacts")
    lead = relationship("Lead", back_populates="contacts")
