from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal

class InvoiceItemBase(BaseModel):
    product_id: Optional[int] = None
    description: Optional[str] = None
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItemResponse(InvoiceItemBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    invoice_number: str
    amount: Decimal
    currency: str = "ARS"
    exchange_rate: Optional[Decimal] = 1
    amount_ars: Optional[Decimal] = None
    file_url: Optional[str] = None
    type: Optional[str] = "created"
    issue_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None
    status_id: Optional[int] = None
    client_id: Optional[int] = None
    provider_id: Optional[int] = None
    quote_id: Optional[int] = None
    sales_order_id: Optional[int] = None
    seller_id: Optional[int] = None
    # ARCA fields
    arca_cbte_tipo: Optional[int] = None
    arca_punto_vta: Optional[int] = None
    arca_cbte_nro: Optional[int] = None
    arca_concepto: Optional[int] = None
    arca_tipo_doc_receptor: Optional[int] = None
    arca_nro_doc_receptor: Optional[str] = None
    arca_condicion_iva_receptor: Optional[int] = None
    cae: Optional[str] = None
    cae_vto: Optional[date] = None
    arca_result: Optional[str] = None
    arca_obs: Optional[str] = None
    imp_neto: Optional[Decimal] = None
    imp_iva: Optional[Decimal] = None
    imp_tot_conc: Optional[Decimal] = None
    imp_op_ex: Optional[Decimal] = None
    imp_trib: Optional[Decimal] = None
    mon_id: Optional[str] = None
    mon_cotiz: Optional[Decimal] = None
    # Associated invoice (for NC/ND)
    cbte_asoc_tipo: Optional[int] = None
    cbte_asoc_pto_vta: Optional[int] = None
    cbte_asoc_nro: Optional[int] = None
    cbte_asoc_cuit: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    items: Optional[List[InvoiceItemCreate]] = []

class InvoiceUpdate(InvoiceBase):
    invoice_number: Optional[str] = None
    amount: Optional[Decimal] = None
    items: Optional[List[InvoiceItemCreate]] = None

class InvoiceInDBBase(InvoiceBase):
    id: int

    class Config:
        from_attributes = True

class InvoiceResponse(InvoiceInDBBase):
    items: List[InvoiceItemResponse] = []

class InvoiceStatusBase(BaseModel):
    name: str
    description: Optional[str] = None
    color_code: Optional[str] = "#3B82F6"

class InvoiceStatusCreate(InvoiceStatusBase):
    pass

class InvoiceStatusUpdate(InvoiceStatusBase):
    name: Optional[str] = None

class InvoiceStatusResponse(InvoiceStatusBase):
    id: int

    class Config:
        from_attributes = True
