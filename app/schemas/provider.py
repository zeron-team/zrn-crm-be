from pydantic import BaseModel, EmailStr
from typing import Optional

class ProviderBase(BaseModel):
    name: str
    cuit_dni: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = True

class ProviderCreate(ProviderBase):
    pass

class ProviderUpdate(ProviderBase):
    name: Optional[str] = None

class ProviderInDBBase(ProviderBase):
    id: int

    class Config:
        from_attributes = True

class ProviderResponse(ProviderInDBBase):
    pass
