from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    name: str                                  # Razón Social
    trade_name: Optional[str] = None           # Nombre Comercial
    tax_condition: Optional[str] = None        # Condición de IVA
    cuit_dni: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None              # Dirección
    city: Optional[str] = None                 # Localidad
    province: Optional[str] = None             # Provincia
    country: Optional[str] = None              # País
    website: Optional[str] = None              # Sitio Web
    activity: Optional[str] = None             # Actividad principal (AFIP)
    arca_validated: Optional[bool] = False     # Validated via ARCA
    arca_validated_at: Optional[datetime] = None
    is_active: Optional[bool] = True
    seller_id: Optional[int] = None

class ClientCreate(ClientBase):
    pass

class ClientUpdate(ClientBase):
    name: Optional[str] = None

class ClientInDBBase(ClientBase):
    id: int

    class Config:
        from_attributes = True

class ClientResponse(ClientInDBBase):
    pass
