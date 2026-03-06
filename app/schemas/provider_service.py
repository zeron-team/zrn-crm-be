from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

class ProviderServiceBase(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = Field(default=None, max_length=255)
    cost_price: float = Field(..., gt=-1)
    currency: str = Field(default="USD")
    billing_cycle: str = Field(default="Monthly")
    expiration_date: date
    notify_days_before: int = Field(default=3, ge=0)
    status: str = Field(default="Active")

class ProviderServiceCreate(ProviderServiceBase):
    provider_id: int

class ProviderServiceUpdate(BaseModel):
    product_id: Optional[int] = None
    name: Optional[str] = None
    cost_price: Optional[float] = None
    currency: Optional[str] = None
    billing_cycle: Optional[str] = None
    expiration_date: Optional[date] = None
    notify_days_before: Optional[int] = None
    status: Optional[str] = None

class ProviderServiceResponse(ProviderServiceBase):
    id: int
    provider_id: int
    product_name: Optional[str] = None
    product_family: Optional[str] = None
    product_category: Optional[str] = None
    product_subcategory: Optional[str] = None

    class Config:
        from_attributes = True
