from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from typing import Optional
import os
import shutil

from app.database import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceStatusCreate, InvoiceStatusUpdate, InvoiceStatusResponse
from app.services.invoice import invoice_service, invoice_status_service

router = APIRouter()

@router.post("/statuses", response_model=InvoiceStatusResponse)
def create_status(status_in: InvoiceStatusCreate, db: Session = Depends(get_db)):
    return invoice_status_service.create_status(db, status_in=status_in)

@router.get("/statuses", response_model=List[InvoiceStatusResponse])
def read_statuses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return invoice_status_service.get_statuses(db, skip=skip, limit=limit)

@router.put("/statuses/{status_id}", response_model=InvoiceStatusResponse)
def update_status(status_id: int, status_in: InvoiceStatusUpdate, db: Session = Depends(get_db)):
    return invoice_status_service.update_status(db, status_id=status_id, status_in=status_in)

@router.delete("/statuses/{status_id}", response_model=InvoiceStatusResponse)
def delete_status(status_id: int, db: Session = Depends(get_db)):
    return invoice_status_service.delete_status(db, status_id=status_id)

@router.post("/", response_model=InvoiceResponse)
def create_invoice(invoice_in: InvoiceCreate, db: Session = Depends(get_db)):
    inv = invoice_service.create_invoice(db, invoice_in=invoice_in)
    # Log creation
    from app.models.invoice_audit_log import InvoiceAuditLog
    log = InvoiceAuditLog(
        invoice_id=inv.id,
        action="created",
        description=f"Factura {inv.invoice_number} creada",
        new_value=inv.invoice_number,
        user_name="Sistema",
    )
    db.add(log)
    db.commit()
    return inv

@router.get("/", response_model=List[InvoiceResponse])
def read_invoices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return invoice_service.get_invoices(db, skip=skip, limit=limit)

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def read_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return invoice_service.get_invoice(db, invoice_id=invoice_id)

@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(invoice_id: int, invoice_in: InvoiceUpdate, db: Session = Depends(get_db)):
    return invoice_service.update_invoice(db, invoice_id=invoice_id, invoice_in=invoice_in)

@router.delete("/{invoice_id}", response_model=InvoiceResponse)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return invoice_service.delete_invoice(db, invoice_id=invoice_id)

@router.post("/{invoice_id}/upload", response_model=InvoiceResponse)
def upload_invoice_file(invoice_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Verify invoice exists first
    invoice = invoice_service.get_invoice(db, invoice_id=invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    os.makedirs("uploads/invoices", exist_ok=True)
    file_extension = os.path.splitext(file.filename)[1]
    safe_filename = f"{invoice_id}{file_extension}"
    file_path = os.path.join("uploads/invoices", safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    file_url = f"/uploads/invoices/{safe_filename}"
    return invoice_service.update_file_url(db, invoice_id=invoice_id, file_url=file_url)


# ─── Quick Status Change ──────────────────────────────────

class StatusChangeRequest(BaseModel):
    status_id: int
    user_name: Optional[str] = "Sistema"

@router.patch("/{invoice_id}/status")
def change_invoice_status(invoice_id: int, req: StatusChangeRequest, db: Session = Depends(get_db)):
    """Change invoice status and log the change."""
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.invoice_audit_log import InvoiceAuditLog

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    old_status = db.query(InvoiceStatus).filter(InvoiceStatus.id == invoice.status_id).first() if invoice.status_id else None
    new_status = db.query(InvoiceStatus).filter(InvoiceStatus.id == req.status_id).first()
    if not new_status:
        raise HTTPException(status_code=404, detail="Status not found")

    old_name = old_status.name if old_status else "Sin estado"
    invoice.status_id = req.status_id
    
    log = InvoiceAuditLog(
        invoice_id=invoice_id,
        action="status_changed",
        description=f"Estado cambiado de '{old_name}' a '{new_status.name}'",
        old_value=old_name,
        new_value=new_status.name,
        user_name=req.user_name,
    )
    db.add(log)
    db.commit()
    db.refresh(invoice)
    return {"success": True, "status_id": req.status_id, "status_name": new_status.name}


# ─── Audit Log ─────────────────────────────────────────────

@router.get("/{invoice_id}/audit-log")
def get_invoice_audit_log(invoice_id: int, db: Session = Depends(get_db)):
    """Get the full audit history for an invoice."""
    from app.models.invoice import Invoice
    from app.models.invoice_audit_log import InvoiceAuditLog

    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    logs = db.query(InvoiceAuditLog).filter(
        InvoiceAuditLog.invoice_id == invoice_id
    ).order_by(InvoiceAuditLog.created_at.desc()).all()

    # If no logs exist, seed initial entry from invoice data
    if not logs:
        seed_logs = []
        seed_logs.append(InvoiceAuditLog(
            invoice_id=invoice_id,
            action="created",
            description=f"Factura {invoice.invoice_number} creada",
            new_value=invoice.invoice_number,
            user_name="Sistema",
            created_at=invoice.issue_date if invoice.issue_date else None,
        ))
        if invoice.cae:
            seed_logs.append(InvoiceAuditLog(
                invoice_id=invoice_id,
                action="arca_emitted",
                description=f"Emitida en ARCA - CAE: {invoice.cae}",
                new_value=invoice.cae,
                user_name="Sistema",
                created_at=invoice.issue_date if invoice.issue_date else None,
            ))
        if invoice.cbte_asoc_nro:
            seed_logs.append(InvoiceAuditLog(
                invoice_id=invoice_id,
                action="nc_associated",
                description=f"Asociada a comprobante {invoice.cbte_asoc_pto_vta}-{invoice.cbte_asoc_nro}",
                new_value=f"{invoice.cbte_asoc_pto_vta}-{invoice.cbte_asoc_nro}",
                user_name="Sistema",
                created_at=invoice.issue_date if invoice.issue_date else None,
            ))
        for log in seed_logs:
            db.add(log)
        db.commit()
        logs = db.query(InvoiceAuditLog).filter(
            InvoiceAuditLog.invoice_id == invoice_id
        ).order_by(InvoiceAuditLog.created_at.desc()).all()

    # Also check for associated NC/ND
    associated = []
    if invoice.arca_cbte_tipo in (1, 6, 11):  # It's a regular invoice, check for NCs referencing it
        assoc_invoices = db.query(Invoice).filter(
            Invoice.cbte_asoc_nro == str(invoice.arca_cbte_nro),
            Invoice.cbte_asoc_pto_vta == str(invoice.arca_punto_vta),
            Invoice.cbte_asoc_tipo == str(invoice.arca_cbte_tipo),
            Invoice.id != invoice_id,
        ).all()
        for ai in assoc_invoices:
            tipo_name = "Nota de Crédito" if ai.arca_cbte_tipo in (3, 8, 13) else "Nota de Débito" if ai.arca_cbte_tipo in (2, 7, 12) else "Comprobante"
            associated.append({
                "id": ai.id,
                "invoice_number": ai.invoice_number,
                "type": tipo_name,
                "amount": float(ai.amount) if ai.amount else 0,
                "cae": ai.cae,
                "date": str(ai.issue_date) if ai.issue_date else None,
            })

    return {
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "logs": [
            {
                "id": l.id,
                "action": l.action,
                "description": l.description,
                "old_value": l.old_value,
                "new_value": l.new_value,
                "user_name": l.user_name,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ],
        "associated_documents": associated,
    }

