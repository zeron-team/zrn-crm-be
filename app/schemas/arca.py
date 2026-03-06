from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


# --- ARCA Configuration ---

class ArcaConfigBase(BaseModel):
    cuit: str
    razon_social: str
    condicion_iva: int = 1                  # 1=Resp.Inscripto, 6=Monotributo
    punto_vta: int
    domicilio_comercial: Optional[str] = None
    inicio_actividades: Optional[date] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    environment: str = "homologacion"       # "homologacion" / "produccion"
    is_active: bool = True


class ArcaConfigCreate(ArcaConfigBase):
    pass


class ArcaConfigUpdate(BaseModel):
    cuit: Optional[str] = None
    razon_social: Optional[str] = None
    condicion_iva: Optional[int] = None
    punto_vta: Optional[int] = None
    domicilio_comercial: Optional[str] = None
    inicio_actividades: Optional[date] = None
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None


class ArcaConfigResponse(ArcaConfigBase):
    id: int

    class Config:
        from_attributes = True


# --- IVA Items ---

class IvaItemRequest(BaseModel):
    iva_id: int                             # 3=0%, 4=10.5%, 5=21%, 6=27%
    base_imp: Decimal                       # Base imponible
    importe: Decimal                        # Monto IVA


class IvaItemResponse(IvaItemRequest):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True


# --- ARCA Emit Request ---

class ArcaEmitRequest(BaseModel):
    """Request to emit an electronic invoice via ARCA"""
    invoice_id: int                         # ID of the invoice in Zeron CRM
    cbte_tipo: int                          # Voucher type (1=A, 6=B, 11=C)
    concepto: int = 1                       # 1=Products, 2=Services, 3=Both
    tipo_doc: int = 80                      # Doc type (80=CUIT, 96=DNI, 99=CF)
    nro_doc: str                            # Receptor document number
    condicion_iva_receptor: int             # Receptor IVA condition (RG5616)
    imp_neto: Decimal                       # Net taxable amount
    imp_iva: Decimal                        # Total IVA amount
    imp_total: Decimal                      # Total with IVA
    imp_tot_conc: Decimal = Decimal("0")    # Non-taxable
    imp_op_ex: Decimal = Decimal("0")       # Exempt
    imp_trib: Decimal = Decimal("0")        # Other taxes
    fecha_cbte: Optional[str] = None        # Format: YYYYMMDD (defaults to today)
    fecha_venc_pago: Optional[str] = None   # Format: YYYYMMDD
    mon_id: str = "PES"                     # Currency code (PES=ARS, DOL=USD, 060=EUR)
    mon_cotiz: Decimal = Decimal("1.000")   # Exchange rate
    iva_items: List[IvaItemRequest] = []    # IVA breakdown
    # Service-specific dates (required if concepto=2 or 3)
    fecha_serv_desde: Optional[str] = None
    fecha_serv_hasta: Optional[str] = None
    # Associated invoice (required for NC/ND - credit & debit notes)
    cbte_asoc_tipo: Optional[int] = None       # Type of associated invoice
    cbte_asoc_pto_vta: Optional[int] = None    # Point of sale of associated invoice
    cbte_asoc_nro: Optional[int] = None        # Number of associated invoice
    cbte_asoc_cuit: Optional[str] = None       # CUIT of associated invoice emitter
    cbte_asoc_fecha: Optional[str] = None      # Date of associated invoice (YYYYMMDD)


class ArcaEmitResponse(BaseModel):
    """Response from ARCA after emitting an invoice"""
    success: bool
    cae: Optional[str] = None
    cae_vto: Optional[str] = None
    cbte_nro: Optional[int] = None
    resultado: Optional[str] = None         # A=Approved, R=Rejected
    observaciones: Optional[str] = None
    errores: Optional[str] = None
    invoice_id: int


# --- ARCA Query Responses ---

class ArcaLastVoucherResponse(BaseModel):
    cbte_nro: int
    cbte_tipo: int
    punto_vta: int


class ArcaVoucherTypeResponse(BaseModel):
    id: int
    desc: str


class ArcaIvaTypeResponse(BaseModel):
    id: int
    desc: str


class ArcaCurrencyRateResponse(BaseModel):
    mon_id: str
    mon_cotiz: float
    fecha: str


class ArcaPointOfSaleResponse(BaseModel):
    nro: int
    emision_tipo: str
    bloqueado: str
    fecha_baja: Optional[str] = None


class ArcaConnectionTestResponse(BaseModel):
    success: bool
    message: str
    environment: str
    server_time: Optional[str] = None
