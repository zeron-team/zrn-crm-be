from pydantic import BaseModel
from typing import Optional, Union
from datetime import date as DateType, datetime
from decimal import Decimal

class ExchangeRateCreate(BaseModel):
    date: DateType
    currency: str = "USD"
    buy_rate: Decimal
    sell_rate: Decimal
    source: str = "manual"
    created_by: Optional[str] = None

class ExchangeRateUpdate(BaseModel):
    date: Optional[DateType] = None
    currency: Optional[str] = None
    buy_rate: Optional[Decimal] = None
    sell_rate: Optional[Decimal] = None
    source: Optional[str] = None
    updated_by: Optional[str] = None

    model_config = {"extra": "allow"}

class ExchangeRateResponse(BaseModel):
    id: int
    date: DateType
    currency: str
    buy_rate: Decimal
    sell_rate: Decimal
    source: str
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    updated_by: Optional[str] = None

    class Config:
        from_attributes = True
