from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: Optional[Decimal] = 0.0
    currency: str = "ARS"
    type: Optional[str] = "product"
    category: Optional[str] = None
    family: Optional[str] = None
    subcategory: Optional[str] = None
    is_active: Optional[bool] = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(ProductBase):
    name: Optional[str] = None

class ProductInDBBase(ProductBase):
    id: int

    class Config:
        from_attributes = True

class ProductResponse(ProductInDBBase):
    pass
