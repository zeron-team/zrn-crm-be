from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from decimal import Decimal

class ServicePaymentCreate(BaseModel):
    provider_service_id: int
    period_month: int
    period_year: int
    amount: Decimal
    currency: str = "USD"
    payment_date: datetime
    invoice_number: Optional[str] = None
    created_by: Optional[str] = None

class ServicePaymentUpdate(BaseModel):
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    payment_date: Optional[datetime] = None
    invoice_number: Optional[str] = None
    updated_by: Optional[str] = None

class ServicePaymentResponse(BaseModel):
    id: int
    provider_service_id: int
    period_month: int
    period_year: int
    amount: Decimal
    currency: str = "USD"
    exchange_rate: Optional[Decimal] = None
    amount_ars: Optional[Decimal] = None
    payment_date: datetime
    invoice_number: Optional[str] = None
    receipt_file: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True
