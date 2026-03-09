"""Accounting module — Periods, entries, tax obligations, and dashboard.
All accounting belongs to the company itself (from CompanySettings), not clients.
"""
from typing import Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, extract
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.accounting import AccountingPeriod, AccountingEntry, TaxObligation
from app.models.company_settings import CompanySettings
from app.models.invoice import Invoice
from app.models.purchase_order import PurchaseOrder
from app.models.user import User
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/accounting", tags=["accounting"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Schemas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class PeriodCreate(BaseModel):
    month: int
    year: int
    notes: Optional[str] = None

class PeriodUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None

class EntryCreate(BaseModel):
    concept: str
    category: str  # ingreso, egreso, impuesto, carga_social, retencion, percepcion
    subcategory: Optional[str] = None
    amount: float = 0
    tax_rate: Optional[float] = None
    tax_amount: float = 0
    reference: Optional[str] = None
    date: Optional[date] = None
    notes: Optional[str] = None

class EntryUpdate(BaseModel):
    concept: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    amount: Optional[float] = None
    tax_rate: Optional[float] = None
    tax_amount: Optional[float] = None
    reference: Optional[str] = None
    date: Optional[date] = None
    notes: Optional[str] = None

class ObligationCreate(BaseModel):
    tax_type: str
    period_month: Optional[int] = None
    period_year: int
    due_date: date
    amount: float = 0
    notes: Optional[str] = None

class ObligationUpdate(BaseModel):
    status: Optional[str] = None
    amount: Optional[float] = None
    filed_date: Optional[date] = None
    payment_date: Optional[date] = None
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[date] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helpers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MONTH_NAMES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def recalc_period(db: Session, period: AccountingPeriod):
    """Recalculate period totals from entries."""
    cats = {}
    for e in period.entries:
        cats.setdefault(e.category, 0)
        cats[e.category] += (e.amount or 0)
    period.total_ingresos = cats.get("ingreso", 0)
    period.total_egresos = cats.get("egreso", 0)
    period.total_impuestos = cats.get("impuesto", 0)
    period.total_cargas_sociales = cats.get("carga_social", 0)
    period.total_retenciones = cats.get("retencion", 0)
    period.total_percepciones = cats.get("percepcion", 0)
    db.commit()

def get_company(db: Session):
    """Return company settings or empty dict."""
    s = db.query(CompanySettings).first()
    if not s:
        return {}
    return {
        "company_name": s.company_name or "Mi Empresa",
        "fantasy_name": s.fantasy_name,
        "cuit": s.cuit,
        "logo_url": s.logo_url,
        "legal_name": s.legal_name,
        "address": s.address,
        "city": s.city,
        "province": s.province,
        "country": s.country,
        "phone": s.phone,
        "email": s.email,
        "iva_condition": s.iva_condition,
        "default_currency": getattr(s, "default_currency", "ARS") or "ARS",
        "timezone": getattr(s, "timezone", "America/Argentina/Buenos_Aires"),
    }

def period_to_dict(p: AccountingPeriod, db: Session):
    creator = db.query(User).get(p.created_by) if p.created_by else None
    return {
        "id": p.id,
        "month": p.month,
        "month_name": MONTH_NAMES[p.month] if 1 <= p.month <= 12 else str(p.month),
        "year": p.year,
        "status": p.status,
        "total_ingresos": p.total_ingresos or 0,
        "total_egresos": p.total_egresos or 0,
        "total_impuestos": p.total_impuestos or 0,
        "total_cargas_sociales": p.total_cargas_sociales or 0,
        "total_retenciones": p.total_retenciones or 0,
        "total_percepciones": p.total_percepciones or 0,
        "notes": p.notes,
        "created_by": p.created_by,
        "created_by_name": creator.full_name if creator else None,
        "entry_count": len(p.entries),
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }

def entry_to_dict(e: AccountingEntry):
    return {
        "id": e.id, "period_id": e.period_id,
        "concept": e.concept, "category": e.category, "subcategory": e.subcategory,
        "amount": e.amount or 0, "tax_rate": e.tax_rate, "tax_amount": e.tax_amount or 0,
        "reference": e.reference, "date": e.date.isoformat() if e.date else None,
        "notes": e.notes, "created_at": e.created_at.isoformat() if e.created_at else None,
    }

def obligation_to_dict(o: TaxObligation):
    return {
        "id": o.id,
        "tax_type": o.tax_type,
        "period_month": o.period_month,
        "period_month_name": MONTH_NAMES[o.period_month] if o.period_month and 1 <= o.period_month <= 12 else None,
        "period_year": o.period_year,
        "due_date": o.due_date.isoformat() if o.due_date else None,
        "status": o.status, "amount": o.amount or 0,
        "filed_date": o.filed_date.isoformat() if o.filed_date else None,
        "payment_date": o.payment_date.isoformat() if o.payment_date else None,
        "reference_number": o.reference_number, "notes": o.notes,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Company Context
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/company-context")
def company_context(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Company identity + billing/purchase totals for current year."""
    today = date.today()
    year = today.year

    ventas_q = db.query(
        func.count(Invoice.id).label("count"),
        func.coalesce(func.sum(Invoice.amount), 0).label("total"),
        func.coalesce(func.sum(Invoice.imp_neto), 0).label("neto"),
        func.coalesce(func.sum(Invoice.imp_iva), 0).label("iva"),
    ).filter(Invoice.type == "created", extract("year", Invoice.issue_date) == year).first()

    compras_q = db.query(
        func.count(PurchaseOrder.id).label("count"),
        func.coalesce(func.sum(PurchaseOrder.total_amount), 0).label("total"),
    ).filter(extract("year", PurchaseOrder.created_at) == year).first()

    recibidas_q = db.query(
        func.count(Invoice.id).label("count"),
        func.coalesce(func.sum(Invoice.amount), 0).label("total"),
    ).filter(Invoice.type == "received", extract("year", Invoice.issue_date) == year).first()

    return {
        "company": get_company(db),
        "year": year,
        "ventas": {"count": int(ventas_q.count) if ventas_q else 0, "total": float(ventas_q.total) if ventas_q else 0,
                   "neto": float(ventas_q.neto) if ventas_q else 0, "iva": float(ventas_q.iva) if ventas_q else 0},
        "compras": {"count": int(compras_q.count) if compras_q else 0, "total": float(compras_q.total) if compras_q else 0},
        "recibidas": {"count": int(recibidas_q.count) if recibidas_q else 0, "total": float(recibidas_q.total) if recibidas_q else 0},
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Periods (company-owned, no client selection)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/periods")
def list_periods(
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(AccountingPeriod)
    if year:
        q = q.filter(AccountingPeriod.year == year)
    if status:
        q = q.filter(AccountingPeriod.status == status)
    periods = q.order_by(desc(AccountingPeriod.year), desc(AccountingPeriod.month)).all()
    return [period_to_dict(p, db) for p in periods]


@router.post("/periods", status_code=201)
def create_period(data: PeriodCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    exists = db.query(AccountingPeriod).filter(
        AccountingPeriod.month == data.month,
        AccountingPeriod.year == data.year,
    ).first()
    if exists:
        raise HTTPException(400, f"Ya existe un período {data.month}/{data.year}")
    period = AccountingPeriod(month=data.month, year=data.year, notes=data.notes, created_by=current_user.id)
    db.add(period)
    db.commit()
    db.refresh(period)
    return period_to_dict(period, db)


@router.get("/periods/{period_id}")
def get_period(period_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    period = db.query(AccountingPeriod).get(period_id)
    if not period:
        raise HTTPException(404, "Período no encontrado")
    result = period_to_dict(period, db)
    result["entries"] = [entry_to_dict(e) for e in period.entries]
    return result


@router.put("/periods/{period_id}")
def update_period(period_id: int, data: PeriodUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    period = db.query(AccountingPeriod).get(period_id)
    if not period:
        raise HTTPException(404, "Período no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(period, k, v)
    db.commit()
    db.refresh(period)
    return period_to_dict(period, db)


@router.put("/periods/{period_id}/status")
def update_period_status(period_id: int, data: dict, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    period = db.query(AccountingPeriod).get(period_id)
    if not period:
        raise HTTPException(404, "Período no encontrado")
    new_status = data.get("status")
    valid = ["draft", "in_review", "confirmed", "filed"]
    if new_status not in valid:
        raise HTTPException(400, f"Estado inválido. Válidos: {valid}")
    period.status = new_status
    db.commit()
    return {"ok": True, "status": new_status}


@router.delete("/periods/{period_id}")
def delete_period(period_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    period = db.query(AccountingPeriod).get(period_id)
    if not period:
        raise HTTPException(404, "Período no encontrado")
    if period.status != "draft":
        raise HTTPException(400, "Solo se pueden eliminar períodos en borrador")
    db.delete(period)
    db.commit()
    return {"ok": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Entries
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/periods/{period_id}/entries", status_code=201)
def add_entry(period_id: int, data: EntryCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    period = db.query(AccountingPeriod).get(period_id)
    if not period:
        raise HTTPException(404, "Período no encontrado")
    if period.status not in ("draft", "in_review"):
        raise HTTPException(400, "No se puede agregar ítems a un período confirmado")
    entry = AccountingEntry(**data.model_dump(), period_id=period_id)
    db.add(entry)
    db.commit()
    db.refresh(period)
    recalc_period(db, period)
    db.refresh(entry)
    return entry_to_dict(entry)


@router.put("/entries/{entry_id}")
def update_entry(entry_id: int, data: EntryUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = db.query(AccountingEntry).get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry no encontrado")
    period = db.query(AccountingPeriod).get(entry.period_id)
    if period and period.status not in ("draft", "in_review"):
        raise HTTPException(400, "No se puede modificar ítems de un período confirmado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(entry, k, v)
    db.commit()
    if period:
        db.refresh(period)
        recalc_period(db, period)
    db.refresh(entry)
    return entry_to_dict(entry)


@router.delete("/entries/{entry_id}")
def delete_entry(entry_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    entry = db.query(AccountingEntry).get(entry_id)
    if not entry:
        raise HTTPException(404, "Entry no encontrado")
    period = db.query(AccountingPeriod).get(entry.period_id)
    if period and period.status not in ("draft", "in_review"):
        raise HTTPException(400, "No se puede eliminar ítems de un período confirmado")
    period_id = entry.period_id
    db.delete(entry)
    db.commit()
    if period:
        db.refresh(period)
        recalc_period(db, period)
    return {"ok": True}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Tax Obligations (company-owned)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/obligations")
def list_obligations(
    tax_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = db.query(TaxObligation)
    if tax_type:
        q = q.filter(TaxObligation.tax_type == tax_type)
    if status:
        q = q.filter(TaxObligation.status == status)
    if year:
        q = q.filter(TaxObligation.period_year == year)
    obls = q.order_by(desc(TaxObligation.due_date)).all()
    return [obligation_to_dict(o) for o in obls]


@router.post("/obligations", status_code=201)
def create_obligation(data: ObligationCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obl = TaxObligation(**data.model_dump())
    db.add(obl)
    db.commit()
    db.refresh(obl)
    return obligation_to_dict(obl)


@router.put("/obligations/{obl_id}")
def update_obligation(obl_id: int, data: ObligationUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obl = db.query(TaxObligation).get(obl_id)
    if not obl:
        raise HTTPException(404, "Obligación no encontrada")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obl, k, v)
    db.commit()
    db.refresh(obl)
    return obligation_to_dict(obl)


@router.delete("/obligations/{obl_id}")
def delete_obligation(obl_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obl = db.query(TaxObligation).get(obl_id)
    if not obl:
        raise HTTPException(404, "Obligación no encontrada")
    db.delete(obl)
    db.commit()
    return {"ok": True}


@router.get("/obligations/upcoming")
def upcoming_obligations(days: int = Query(30), db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today = date.today()
    from datetime import timedelta
    end = today + timedelta(days=days)
    obls = db.query(TaxObligation).filter(
        TaxObligation.due_date >= today,
        TaxObligation.due_date <= end,
        TaxObligation.status.in_(["pending", "overdue"]),
    ).order_by(TaxObligation.due_date).all()
    return [obligation_to_dict(o) for o in obls]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Dashboard
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/dashboard")
def accounting_dashboard(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    today = date.today()
    from datetime import timedelta

    total_periods = db.query(AccountingPeriod).count()
    draft_periods = db.query(AccountingPeriod).filter(AccountingPeriod.status == "draft").count()
    confirmed_periods = db.query(AccountingPeriod).filter(AccountingPeriod.status == "confirmed").count()
    filed_periods = db.query(AccountingPeriod).filter(AccountingPeriod.status == "filed").count()

    pending_obls = db.query(TaxObligation).filter(TaxObligation.status.in_(["pending", "overdue"])).count()
    overdue_obls = db.query(TaxObligation).filter(
        TaxObligation.status == "pending",
        TaxObligation.due_date < today,
    ).count()

    # Auto-update overdue
    db.query(TaxObligation).filter(
        TaxObligation.status == "pending",
        TaxObligation.due_date < today,
    ).update({"status": "overdue"}, synchronize_session=False)
    db.commit()

    upcoming = db.query(TaxObligation).filter(
        TaxObligation.due_date >= today,
        TaxObligation.due_date <= today + timedelta(days=15),
        TaxObligation.status.in_(["pending"]),
    ).order_by(TaxObligation.due_date).limit(10).all()

    # Monthly breakdown for current year
    monthly = db.query(
        AccountingPeriod.month,
        func.sum(AccountingPeriod.total_ingresos).label("ingresos"),
        func.sum(AccountingPeriod.total_egresos).label("egresos"),
        func.sum(AccountingPeriod.total_impuestos).label("impuestos"),
    ).filter(AccountingPeriod.year == today.year).group_by(AccountingPeriod.month).order_by(AccountingPeriod.month).all()

    monthly_breakdown = [
        {"month": m.month, "month_name": MONTH_NAMES[m.month] if 1 <= m.month <= 12 else str(m.month),
         "ingresos": float(m.ingresos or 0), "egresos": float(m.egresos or 0), "impuestos": float(m.impuestos or 0)}
        for m in monthly
    ]

    return {
        "company": get_company(db),
        "year": today.year,
        "total_periods": total_periods,
        "draft_periods": draft_periods,
        "confirmed_periods": confirmed_periods,
        "filed_periods": filed_periods,
        "pending_obligations": pending_obls,
        "overdue_obligations": overdue_obls,
        "upcoming_obligations": [obligation_to_dict(o) for o in upcoming],
        "monthly_breakdown": monthly_breakdown,
    }
