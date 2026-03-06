from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.schemas.contact import ContactResponse

class LeadBase(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    status: Optional[str] = "New"
    source: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    notes: Optional[str] = None

class LeadCreate(LeadBase):
    pass

class LeadUpdate(LeadBase):
    company_name: Optional[str] = None

class LeadResponse(LeadBase):
    id: int
    created_at: datetime
    updated_at: datetime
    contacts: List[ContactResponse] = []

    class Config:
        orm_mode = True
