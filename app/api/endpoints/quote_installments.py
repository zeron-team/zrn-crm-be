from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal

from app.database import get_db
from app.models.quote_installment import QuoteInstallment
from app.models.quote import Quote
from app.models.invoice import Invoice

router = APIRouter()


# Schemas
class InstallmentCreate(BaseModel):
    installment_number: int
    amount: Decimal
    due_date: date
    notes: Optional[str] = None

class InstallmentUpdate(BaseModel):
    amount: Optional[Decimal] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    invoice_id: Optional[int] = None
    notes: Optional[str] = None

class InstallmentResponse(BaseModel):
    id: int
    quote_id: int
    installment_number: int
    amount: Decimal
    due_date: date
    status: str
    invoice_id: Optional[int] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class BulkInstallmentsCreate(BaseModel):
    num_installments: int
    total_amount: Decimal
    start_date: date
    notes: Optional[str] = None


def _inst_to_response(inst: QuoteInstallment) -> dict:
    return {
        "id": inst.id,
        "quote_id": inst.quote_id,
        "installment_number": inst.installment_number,
        "amount": inst.amount,
        "due_date": inst.due_date,
        "status": inst.status,
        "invoice_id": inst.invoice_id,
        "invoice_number": inst.invoice.invoice_number if inst.invoice else None,
        "notes": inst.notes,
        "created_at": inst.created_at,
    }


# --- Endpoints ---

@router.get("/{quote_id}/installments", response_model=List[InstallmentResponse])
def list_installments(quote_id: int, db: Session = Depends(get_db)):
    insts = db.query(QuoteInstallment).options(
        joinedload(QuoteInstallment.invoice)
    ).filter(QuoteInstallment.quote_id == quote_id).order_by(
        QuoteInstallment.installment_number
    ).all()
    return [_inst_to_response(i) for i in insts]


@router.post("/{quote_id}/installments/bulk", response_model=List[InstallmentResponse])
def create_bulk_installments(quote_id: int, data: BulkInstallmentsCreate, db: Session = Depends(get_db)):
    """Auto-generate N equal installments for a quote."""
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    # Delete existing installments
    db.query(QuoteInstallment).filter(QuoteInstallment.quote_id == quote_id).delete()

    amount_per = round(float(data.total_amount) / data.num_installments, 2)
    remainder = round(float(data.total_amount) - (amount_per * data.num_installments), 2)

    installments = []
    for i in range(data.num_installments):
        from dateutil.relativedelta import relativedelta
        due = data.start_date + relativedelta(months=i)
        amt = amount_per + (remainder if i == data.num_installments - 1 else 0)
        inst = QuoteInstallment(
            quote_id=quote_id,
            installment_number=i + 1,
            amount=amt,
            due_date=due,
            status="pending",
            notes=data.notes,
        )
        db.add(inst)
        installments.append(inst)

    db.commit()
    for inst in installments:
        db.refresh(inst)
    return [_inst_to_response(i) for i in installments]


@router.post("/{quote_id}/installments", response_model=InstallmentResponse)
def create_installment(quote_id: int, data: InstallmentCreate, db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")

    inst = QuoteInstallment(
        quote_id=quote_id,
        installment_number=data.installment_number,
        amount=data.amount,
        due_date=data.due_date,
        status="pending",
        notes=data.notes,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return _inst_to_response(inst)


@router.put("/installments/{installment_id}", response_model=InstallmentResponse)
def update_installment(installment_id: int, data: InstallmentUpdate, db: Session = Depends(get_db)):
    inst = db.query(QuoteInstallment).filter(QuoteInstallment.id == installment_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Installment not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(inst, field, value)

    # If invoice_id is set, mark as invoiced
    if data.invoice_id is not None:
        inst.status = "invoiced"

    db.commit()
    db.refresh(inst)
    return _inst_to_response(inst)


@router.delete("/installments/{installment_id}")
def delete_installment(installment_id: int, db: Session = Depends(get_db)):
    inst = db.query(QuoteInstallment).filter(QuoteInstallment.id == installment_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Installment not found")
    db.delete(inst)
    db.commit()
    return {"ok": True}
