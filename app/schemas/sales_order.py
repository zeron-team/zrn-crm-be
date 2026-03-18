from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class SalesOrderItemBase(BaseModel):
    product_id: Optional[int] = None
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal


class SalesOrderItemResponse(SalesOrderItemBase):
    id: int
    sales_order_id: int

    class Config:
        from_attributes = True


class SalesOrderCreate(BaseModel):
    """Manual creation — all fields editable"""
    client_id: Optional[int] = None
    seller_id: Optional[int] = None
    quote_id: Optional[int] = None
    currency: str = "ARS"
    notes: Optional[str] = None
    delivery_date: Optional[date] = None
    items: List[SalesOrderItemBase] = []


class SalesOrderUpdate(BaseModel):
    """Full editing support"""
    client_id: Optional[int] = None
    seller_id: Optional[int] = None
    quote_id: Optional[int] = None
    status: Optional[str] = None
    currency: Optional[str] = None
    notes: Optional[str] = None
    delivery_date: Optional[date] = None
    items: Optional[List[SalesOrderItemBase]] = None


class SalesOrderResponse(BaseModel):
    id: int
    order_number: str
    quote_id: Optional[int] = None
    client_id: Optional[int] = None
    seller_id: Optional[int] = None
    status: str
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    notes: Optional[str] = None
    delivery_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    # Enriched fields (populated by endpoint)
    client_name: Optional[str] = None
    seller_name: Optional[str] = None
    quote_number: Optional[str] = None
    items: List[SalesOrderItemResponse] = []
    invoice_count: int = 0

    class Config:
        from_attributes = True
