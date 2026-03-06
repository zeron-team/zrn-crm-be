"""
ARCA (ex AFIP) Electronic Invoicing API Endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
import os
import shutil

from app.database import get_db
from app.schemas.arca import (
    ArcaConfigCreate, ArcaConfigUpdate, ArcaConfigResponse,
    ArcaEmitRequest, ArcaEmitResponse,
    ArcaLastVoucherResponse, ArcaConnectionTestResponse,
)
from app.services.arca_service import arca_service
from app.services.invoice_pdf_service import generate_invoice_pdf_file
from app.models.invoice import Invoice

router = APIRouter()


# ─── Configuration ────────────────────────────────────────

@router.get("/config", response_model=ArcaConfigResponse)
def get_arca_config(db: Session = Depends(get_db)):
    """Get the active ARCA configuration"""
    config = arca_service.get_config(db)
    if not config:
        raise HTTPException(status_code=404, detail="No ARCA configuration found")
    return config


@router.post("/config", response_model=ArcaConfigResponse)
def create_arca_config(config_in: ArcaConfigCreate, db: Session = Depends(get_db)):
    """Create or replace ARCA configuration"""
    return arca_service.create_config(db, config_in)


@router.put("/config/{config_id}", response_model=ArcaConfigResponse)
def update_arca_config(config_id: int, config_in: ArcaConfigUpdate, db: Session = Depends(get_db)):
    """Update ARCA configuration"""
    try:
        return arca_service.update_config(db, config_id, config_in)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/config/upload-cert")
def upload_certificate(
    cert_file: UploadFile = File(..., description="Certificate .crt file"),
    db: Session = Depends(get_db),
):
    """Upload ARCA certificate (.crt)"""
    os.makedirs("arca/certs", exist_ok=True)
    cert_path = "arca/certs/certificado.crt"
    with open(cert_path, "wb") as f:
        shutil.copyfileobj(cert_file.file, f)
    return {"message": "Certificate uploaded", "path": cert_path}


@router.post("/config/upload-key")
def upload_private_key(
    key_file: UploadFile = File(..., description="Private key .key file"),
    db: Session = Depends(get_db),
):
    """Upload ARCA private key (.key)"""
    os.makedirs("arca/certs", exist_ok=True)
    key_path = "arca/certs/clave_privada.key"
    with open(key_path, "wb") as f:
        shutil.copyfileobj(key_file.file, f)
    return {"message": "Private key uploaded", "path": key_path}


# ─── Connection Test ──────────────────────────────────────

@router.post("/test-connection", response_model=ArcaConnectionTestResponse)
def test_arca_connection(db: Session = Depends(get_db)):
    """Test connection to ARCA web services"""
    result = arca_service.test_connection(db)
    return result


# ─── Invoice Emission ─────────────────────────────────────

@router.post("/emit", response_model=ArcaEmitResponse)
def emit_invoice(request: ArcaEmitRequest, db: Session = Depends(get_db)):
    """
    Emit an electronic invoice through ARCA and obtain CAE.
    This is the main operation for electronic invoicing.
    After successful emission, auto-generates the fiscal PDF.
    """
    result = arca_service.emit_invoice(db, request)

    # Auto-generate PDF if emission was successful
    if result.success and result.invoice_id:
        try:
            _generate_pdf_for_invoice(db, result.invoice_id)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"PDF auto-generation failed: {e}")

    return result


def _generate_pdf_for_invoice(db: Session, invoice_id: int) -> str:
    """Helper to generate PDF for an invoice"""
    config = arca_service.get_config(db)
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    # Get client info
    from app.models.client import Client
    client = db.query(Client).filter(Client.id == invoice.client_id).first() if invoice.client_id else None

    # Get line items
    from app.models.invoice_item import InvoiceItem
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).all()

    line_items = []
    for idx, item in enumerate(items):
        code = str(idx + 1).zfill(3)
        # Priority: 1) item.description (edited), 2) product name, 3) fallback
        desc = ""
        if hasattr(item, 'description') and item.description:
            desc = item.description
        elif item.product_id and item.product:
            desc = item.product.name or item.product.description or ""
            code = str(item.product_id).zfill(3)
        if item.product_id:
            code = str(item.product_id).zfill(3)
        line_items.append({
            "codigo": code,
            "descripcion": desc or f"Item {idx + 1}",
            "cantidad": float(item.quantity or 1),
            "unidad": "unidades",
            "precio_unitario": float(item.unit_price or 0),
            "total": float(item.total_price or 0),
        })

    # If no items in DB, create one from invoice amount
    if not line_items:
        line_items.append({
            "codigo": "001",
            "descripcion": invoice.notes or "Servicios profesionales",
            "cantidad": 1,
            "unidad": "unidades",
            "precio_unitario": float(invoice.amount or 0),
            "total": float(invoice.amount or 0),
        })

    invoice_data = {
        "emitter_razon_social": config.razon_social if config else "",
        "emitter_cuit": config.cuit if config else "",
        "emitter_domicilio": config.domicilio_comercial if config else "",
        "emitter_condicion_iva": config.condicion_iva if config else 6,
        "emitter_inicio_act": str(config.inicio_actividades) if config else "",
        "cbte_tipo": invoice.arca_cbte_tipo or 11,
        "punto_vta": invoice.arca_punto_vta or (config.punto_vta if config else 2),
        "cbte_nro": invoice.arca_cbte_nro or 0,
        "concepto": invoice.arca_concepto or 1,
        "tipo_doc": invoice.arca_tipo_doc_receptor or 80,
        "nro_doc": invoice.arca_nro_doc_receptor or "",
        "client_name": client.name if client else "",
        "client_address": client.address if client else "",
        "condicion_iva_receptor": invoice.arca_condicion_iva_receptor or 5,
        "fecha_cbte": str(invoice.issue_date or ""),
        "fecha_venc_pago": str(invoice.due_date or ""),
        "imp_total": float(invoice.amount or 0),
        "imp_neto": float(invoice.imp_neto or invoice.amount or 0),
        "imp_iva": float(invoice.imp_iva or 0),
        "imp_tot_conc": float(invoice.imp_tot_conc or 0),
        "imp_op_ex": float(invoice.imp_op_ex or 0),
        "imp_trib": float(invoice.imp_trib or 0),
        "mon_id": invoice.mon_id or "PES",
        "mon_cotiz": float(invoice.mon_cotiz or 1),
        "cae": invoice.cae or "",
        "cae_vto": str(invoice.cae_vto or ""),
        "line_items": line_items,
    }

    # Add service period dates if available
    if hasattr(invoice, 'issue_date') and invoice.issue_date:
        invoice_data["fecha_serv_desde"] = str(invoice.issue_date)
        invoice_data["fecha_serv_hasta"] = str(invoice.due_date or invoice.issue_date)

    # Add associated invoice for NC/ND
    if invoice.cbte_asoc_tipo and invoice.cbte_asoc_nro:
        invoice_data["cbte_asoc"] = {
            "tipo": invoice.cbte_asoc_tipo,
            "pto_vta": invoice.cbte_asoc_pto_vta or (config.punto_vta if config else 4),
            "nro": invoice.cbte_asoc_nro,
        }

    output_path = f"uploads/invoices/fiscal_{invoice_id}.pdf"
    return generate_invoice_pdf_file(invoice_data, output_path)


# ─── PDF Generation ──────────────────────────────────────

@router.get("/invoice-pdf/{invoice_id}")
def get_invoice_pdf(invoice_id: int, download: int = 0, db: Session = Depends(get_db)):
    """
    Generate and download the fiscal invoice PDF with 3 copies
    (Original, Duplicado, Triplicado) as required by Argentine law.
    Use ?download=1 to force download, otherwise displays inline (for preview).
    """
    pdf_path = f"uploads/invoices/fiscal_{invoice_id}.pdf"

    # If PDF doesn't exist, generate it
    if not os.path.exists(pdf_path):
        try:
            _generate_pdf_for_invoice(db, invoice_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF could not be generated")

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    filename = f"factura_{invoice.invoice_number or invoice_id}.pdf" if invoice else f"factura_{invoice_id}.pdf"

    from starlette.responses import Response
    with open(pdf_path, "rb") as f:
        content = f.read()

    disposition = "attachment" if download else "inline"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        },
    )


# ─── CUIT Lookup ─────────────────────────────────────────

@router.get("/lookup-cuit/{cuit}")
def lookup_cuit(cuit: str, db: Session = Depends(get_db)):
    """
    Query AFIP's Padrón A5 to get taxpayer info by CUIT.
    Returns: razon_social, condicion_iva, domicilio, tipo_persona, actividad.
    """
    try:
        result = arca_service.lookup_cuit(db, cuit)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "CUIT not found"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/last-voucher/{punto_vta}/{cbte_tipo}", response_model=ArcaLastVoucherResponse)
def get_last_voucher(punto_vta: int, cbte_tipo: int, db: Session = Depends(get_db)):
    """Get the last authorized voucher number for a point of sale and voucher type"""
    try:
        return arca_service.get_last_voucher(db, punto_vta, cbte_tipo)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voucher/{punto_vta}/{cbte_tipo}/{cbte_nro}")
def consult_voucher(punto_vta: int, cbte_tipo: int, cbte_nro: int, db: Session = Depends(get_db)):
    """Consult an existing voucher at ARCA"""
    try:
        return arca_service.consult_voucher(db, punto_vta, cbte_tipo, cbte_nro)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/voucher-types")
def get_voucher_types(db: Session = Depends(get_db)):
    """Get available voucher types"""
    try:
        return arca_service.get_voucher_types(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Return fallback types if ARCA is not connected
        from app.services.arca_service import CBTE_TYPES
        return [{"id": k, "desc": v} for k, v in CBTE_TYPES.items()]


@router.get("/iva-types")
def get_iva_types(db: Session = Depends(get_db)):
    """Get available IVA types/rates"""
    return arca_service.get_iva_types(db)


@router.get("/sale-points")
def get_sale_points(db: Session = Depends(get_db)):
    """Get authorized points of sale"""
    try:
        return arca_service.get_sale_points(db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/currency-rate/{mon_id}")
def get_currency_rate(mon_id: str, db: Session = Depends(get_db)):
    """Get exchange rate for a currency from ARCA"""
    try:
        return arca_service.get_currency_rate(db, mon_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
