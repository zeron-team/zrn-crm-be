from typing import Optional, Dict, Any
from datetime import date
from pydantic import BaseModel

class ClientServiceBase(BaseModel):
    client_id: int
    product_id: int
    name: str
    status: str = "Active"
    currency: str = "ARS"
    billing_cycle: str = "Monthly"
    characteristics: Dict[str, Any] = {}
    start_date: date
    end_date: Optional[date] = None

class ClientServiceCreate(ClientServiceBase):
    pass

class ClientServiceUpdate(ClientServiceBase):
    client_id: Optional[int] = None
    product_id: Optional[int] = None
    name: Optional[str] = None
    start_date: Optional[date] = None

class ClientServiceResponse(ClientServiceBase):
    id: int

    class Config:
        orm_mode = True
