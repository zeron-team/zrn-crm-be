from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

# Quote Item Schemas
class QuoteItemBase(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal = Decimal('1.0')
    unit_price: Decimal
    total_price: Decimal

class QuoteItemCreate(QuoteItemBase):
    pass

class QuoteItemUpdate(QuoteItemBase):
    pass

class QuoteItemResponse(QuoteItemBase):
    id: int
    quote_id: int

    class Config:
        from_attributes = True

# Quote Schemas
class QuoteBase(BaseModel):
    client_id: Optional[int] = None
    lead_id: Optional[int] = None
    issue_date: date
    expiry_date: date
    status: str
    currency: str = "ARS"
    subtotal: Decimal = Decimal('0.0')
    tax_amount: Decimal = Decimal('0.0')
    total_amount: Decimal = Decimal('0.0')
    notes: Optional[str] = None
    file_url: Optional[str] = None
    seller_id: Optional[int] = None
    commission_pct: Optional[float] = 0

class QuoteCreate(QuoteBase):
    items: List[QuoteItemCreate]

class QuoteUpdate(QuoteBase):
    quote_number: Optional[str] = None
    items: Optional[List[QuoteItemCreate]] = None

class QuoteResponse(QuoteBase):
    id: int
    quote_number: str
    created_at: datetime
    updated_at: datetime
    items: List[QuoteItemResponse] = []

    class Config:
        from_attributes = True
