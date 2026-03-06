from pydantic import BaseModel, EmailStr
from typing import Optional

class ContactBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    position: Optional[str] = None
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    lead_id: Optional[int] = None

class ContactCreate(ContactBase):
    pass

class ContactUpdate(ContactBase):
    name: Optional[str] = None

class ContactInDBBase(ContactBase):
    id: int

    class Config:
        from_attributes = True

class ContactResponse(ContactInDBBase):
    pass
