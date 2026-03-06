from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models.payroll import PayrollConcept, PayrollPeriod, PayrollSlip, PayrollSlipItem
from app.models.employee import Employee
from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal

router = APIRouter(prefix="/payroll", tags=["payroll"])

# ─── Argentine Labor Law Default Rates ─────────────────────────────
DEFAULTS = [
    {"code": "SUELDO", "name": "Sueldo Básico", "type": "remunerativo", "category": "sueldo", "calc_mode": "fijo", "default_rate": 0, "applies_to": "employee", "is_mandatory": True, "sort_order": 1},
    {"code": "JUB_EMP", "name": "Jubilación (SIPA)", "type": "deduccion", "category": "jubilacion", "calc_mode": "porcentaje", "default_rate": 11.0, "applies_to": "employee", "is_mandatory": True, "sort_order": 10},
    {"code": "PAMI_EMP", "name": "INSSJP (PAMI)", "type": "deduccion", "category": "pami", "calc_mode": "porcentaje", "default_rate": 3.0, "applies_to": "employee", "is_mandatory": True, "sort_order": 11},
    {"code": "OS_EMP", "name": "Obra Social", "type": "deduccion", "category": "obra_social", "calc_mode": "porcentaje", "default_rate": 3.0, "applies_to": "employee", "is_mandatory": True, "sort_order": 12},
    {"code": "SIND", "name": "Cuota Sindical", "type": "deduccion", "category": "sindicato", "calc_mode": "porcentaje", "default_rate": 2.0, "applies_to": "employee", "is_mandatory": False, "sort_order": 13},
    {"code": "JUB_PAT", "name": "Jubilación Patronal", "type": "deduccion", "category": "jubilacion", "calc_mode": "porcentaje", "default_rate": 10.17, "applies_to": "employer", "is_mandatory": True, "sort_order": 20},
    {"code": "PAMI_PAT", "name": "INSSJP Patronal", "type": "deduccion", "category": "pami", "calc_mode": "porcentaje", "default_rate": 1.5, "applies_to": "employer", "is_mandatory": True, "sort_order": 21},
    {"code": "OS_PAT", "name": "Obra Social Patronal", "type": "deduccion", "category": "obra_social", "calc_mode": "porcentaje", "default_rate": 6.0, "applies_to": "employer", "is_mandatory": True, "sort_order": 22},
    {"code": "FNE", "name": "Fondo Nac. de Empleo", "type": "deduccion", "category": "otro", "calc_mode": "porcentaje", "default_rate": 0.89, "applies_to": "employer", "is_mandatory": True, "sort_order": 23},
    {"code": "ASIG_FAM", "name": "Asignaciones Familiares", "type": "deduccion", "category": "otro", "calc_mode": "porcentaje", "default_rate": 4.44, "applies_to": "employer", "is_mandatory": True, "sort_order": 24},
    {"code": "ART", "name": "ART (Riesgos del Trabajo)", "type": "deduccion", "category": "otro", "calc_mode": "porcentaje", "default_rate": 2.5, "applies_to": "employer", "is_mandatory": True, "sort_order": 25},
    {"code": "SEG_VIDA", "name": "Seguro de Vida Obligatorio", "type": "deduccion", "category": "otro", "calc_mode": "fijo", "default_rate": 0, "applies_to": "employer", "is_mandatory": True, "sort_order": 26},
]

MONTH_NAMES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
               "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


# ─── Pydantic Schemas ──────────────────────────────────────────────

class ConceptCreate(BaseModel):
    code: str
    name: str
    type: str
    category: Optional[str] = "otro"
    calc_mode: str = "porcentaje"
    default_rate: Optional[float] = 0
    applies_to: str = "employee"
    is_mandatory: bool = False
    sort_order: int = 0


class PeriodCreate(BaseModel):
    year: int
    month: int
    period_type: str = "monthly"
    notes: Optional[str] = None


class SlipItemUpdate(BaseModel):
    concept_id: Optional[int] = None
    concept_name: str
    type: str
    rate: Optional[float] = None
    base_amount: Optional[float] = None
    amount: float
    sort_order: int = 0


class SlipUpdate(BaseModel):
    notes: Optional[str] = None
    extra_items: Optional[list[SlipItemUpdate]] = None


# ─── Serializers ───────────────────────────────────────────────────

def serialize_concept(c: PayrollConcept) -> dict:
    return {
        "id": c.id, "code": c.code, "name": c.name, "type": c.type,
        "category": c.category, "calc_mode": c.calc_mode,
        "default_rate": float(c.default_rate) if c.default_rate else 0,
        "applies_to": c.applies_to, "is_mandatory": c.is_mandatory,
        "is_active": c.is_active, "sort_order": c.sort_order,
    }


def serialize_period(p: PayrollPeriod) -> dict:
    slip_count = len(p.slips) if p.slips else 0
    total_net = sum(float(s.net_salary or 0) for s in (p.slips or []))
    total_cost = sum(float(s.total_employer_cost or 0) for s in (p.slips or []))
    return {
        "id": p.id, "year": p.year, "month": p.month,
        "description": p.description or f"{MONTH_NAMES[p.month]} {p.year}",
        "period_type": p.period_type, "status": p.status, "notes": p.notes,
        "slip_count": slip_count, "total_net": round(total_net, 2),
        "total_employer_cost": round(total_cost, 2),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def serialize_slip(s: PayrollSlip, include_items=False) -> dict:
    emp_name = ""
    legajo = ""
    department = ""
    if s.employee:
        emp_name = f"{s.employee.first_name} {s.employee.last_name}"
        legajo = s.employee.legajo or ""
        department = s.employee.department or ""
    d = {
        "id": s.id, "period_id": s.period_id, "employee_id": s.employee_id,
        "employee_name": emp_name, "legajo": legajo, "department": department,
        "gross_salary": float(s.gross_salary or 0),
        "total_remunerativo": float(s.total_remunerativo or 0),
        "total_no_remunerativo": float(s.total_no_remunerativo or 0),
        "total_deductions": float(s.total_deductions or 0),
        "net_salary": float(s.net_salary or 0),
        "total_employer_cost": float(s.total_employer_cost or 0),
        "status": s.status, "payment_date": s.payment_date.isoformat() if s.payment_date else None,
        "notes": s.notes,
    }
    if include_items:
        d["items"] = [
            {
                "id": i.id, "concept_id": i.concept_id, "concept_code": i.concept_code,
                "concept_name": i.concept_name, "type": i.type,
                "rate": float(i.rate) if i.rate else None,
                "base_amount": float(i.base_amount) if i.base_amount else None,
                "amount": float(i.amount or 0), "sort_order": i.sort_order,
            }
            for i in sorted(s.items, key=lambda x: x.sort_order or 0)
        ]
    return d


# ─── Concepts CRUD ─────────────────────────────────────────────────

@router.get("/concepts")
def list_concepts(db: Session = Depends(get_db)):
    return [serialize_concept(c) for c in db.query(PayrollConcept).order_by(PayrollConcept.sort_order).all()]


@router.post("/concepts", status_code=201)
def create_concept(data: ConceptCreate, db: Session = Depends(get_db)):
    c = PayrollConcept(**data.model_dump())
    c.is_active = True
    db.add(c)
    db.commit()
    db.refresh(c)
    return serialize_concept(c)


@router.put("/concepts/{cid}")
def update_concept(cid: int, data: ConceptCreate, db: Session = Depends(get_db)):
    c = db.query(PayrollConcept).filter(PayrollConcept.id == cid).first()
    if not c:
        raise HTTPException(404, "Concept not found")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return serialize_concept(c)


@router.delete("/concepts/{cid}", status_code=204)
def delete_concept(cid: int, db: Session = Depends(get_db)):
    c = db.query(PayrollConcept).filter(PayrollConcept.id == cid).first()
    if not c:
        raise HTTPException(404, "Concept not found")
    db.delete(c)
    db.commit()


@router.post("/concepts/seed-defaults")
def seed_defaults(db: Session = Depends(get_db)):
    """Seed the default Argentine payroll concepts if they don't exist."""
    existing = {c.code for c in db.query(PayrollConcept).all()}
    added = 0
    for d in DEFAULTS:
        if d["code"] not in existing:
            c = PayrollConcept(**d, is_active=True)
            db.add(c)
            added += 1
    db.commit()
    return {"message": f"Added {added} default concepts", "total": len(DEFAULTS)}


# ─── Periods CRUD ──────────────────────────────────────────────────

@router.get("/periods")
def list_periods(year: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(PayrollPeriod).options(joinedload(PayrollPeriod.slips))
    if year:
        q = q.filter(PayrollPeriod.year == year)
    return [serialize_period(p) for p in q.order_by(PayrollPeriod.year.desc(), PayrollPeriod.month.desc()).all()]


@router.post("/periods", status_code=201)
def create_period(data: PeriodCreate, db: Session = Depends(get_db)):
    existing = db.query(PayrollPeriod).filter(
        PayrollPeriod.year == data.year,
        PayrollPeriod.month == data.month,
        PayrollPeriod.period_type == data.period_type,
    ).first()
    if existing:
        raise HTTPException(400, f"Period {data.month}/{data.year} ({data.period_type}) already exists")
    p = PayrollPeriod(
        year=data.year, month=data.month,
        description=f"{MONTH_NAMES[data.month]} {data.year}",
        period_type=data.period_type, notes=data.notes,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return serialize_period(p)


@router.delete("/periods/{pid}", status_code=204)
def delete_period(pid: int, db: Session = Depends(get_db)):
    p = db.query(PayrollPeriod).filter(PayrollPeriod.id == pid).first()
    if not p:
        raise HTTPException(404, "Period not found")
    if p.status != "draft":
        raise HTTPException(400, "Only draft periods can be deleted")
    db.delete(p)
    db.commit()


@router.put("/periods/{pid}/confirm")
def confirm_period(pid: int, db: Session = Depends(get_db)):
    p = db.query(PayrollPeriod).filter(PayrollPeriod.id == pid).first()
    if not p:
        raise HTTPException(404, "Period not found")
    p.status = "confirmed"
    for slip in p.slips:
        slip.status = "confirmed"
    db.commit()
    return {"message": "Period confirmed"}


@router.put("/periods/{pid}/pay")
def mark_paid(pid: int, db: Session = Depends(get_db)):
    p = db.query(PayrollPeriod).filter(PayrollPeriod.id == pid).first()
    if not p:
        raise HTTPException(404, "Period not found")
    today = date.today()
    p.status = "paid"
    for slip in p.slips:
        slip.status = "paid"
        slip.payment_date = today
    db.commit()
    return {"message": "Period marked as paid"}


# ─── Generate Slips ────────────────────────────────────────────────

@router.post("/periods/{pid}/generate")
def generate_slips(pid: int, db: Session = Depends(get_db)):
    """Generate payroll slips for all active employees with salary > 0."""
    period = db.query(PayrollPeriod).filter(PayrollPeriod.id == pid).first()
    if not period:
        raise HTTPException(404, "Period not found")
    if period.status != "draft":
        raise HTTPException(400, "Can only generate slips for draft periods")

    # Get concepts
    concepts = db.query(PayrollConcept).filter(PayrollConcept.is_active == True).order_by(PayrollConcept.sort_order).all()
    emp_concepts = [c for c in concepts if c.applies_to in ("employee", "both")]
    pat_concepts = [c for c in concepts if c.applies_to in ("employer", "both")]

    # Get active employees with salary
    employees = db.query(Employee).filter(Employee.is_active == True, Employee.salary > 0).all()

    # Remove existing slips for this period
    db.query(PayrollSlip).filter(PayrollSlip.period_id == pid).delete()
    db.flush()

    created = 0
    for emp in employees:
        gross = float(emp.salary or 0)
        if gross <= 0:
            continue

        slip = PayrollSlip(
            period_id=pid, employee_id=emp.id,
            gross_salary=Decimal(str(gross)),
        )
        db.add(slip)
        db.flush()  # get slip.id

        items = []
        total_rem = gross
        total_no_rem = 0.0
        total_ded = 0.0
        total_employer = 0.0

        # 1. Sueldo Básico item
        items.append(PayrollSlipItem(
            slip_id=slip.id, concept_code="SUELDO", concept_name="Sueldo Básico",
            type="remunerativo", rate=None, base_amount=Decimal(str(gross)),
            amount=Decimal(str(gross)), sort_order=1,
        ))

        # 2. Employee deductions
        for c in emp_concepts:
            if c.code == "SUELDO":
                continue
            if c.calc_mode == "porcentaje" and c.default_rate:
                rate = float(c.default_rate)
                amt = round(gross * rate / 100, 2)
            elif c.calc_mode == "fijo":
                rate = None
                amt = float(c.default_rate or 0)
            else:
                continue

            if amt <= 0 and c.calc_mode == "porcentaje":
                continue

            items.append(PayrollSlipItem(
                slip_id=slip.id, concept_id=c.id,
                concept_code=c.code, concept_name=c.name,
                type=c.type, rate=Decimal(str(rate)) if rate else None,
                base_amount=Decimal(str(gross)),
                amount=Decimal(str(amt)), sort_order=c.sort_order or 50,
            ))
            if c.type == "deduccion":
                total_ded += amt
            elif c.type == "no_remunerativo":
                total_no_rem += amt

        # 3. Employer costs
        for c in pat_concepts:
            if c.calc_mode == "porcentaje" and c.default_rate:
                rate = float(c.default_rate)
                amt = round(gross * rate / 100, 2)
            elif c.calc_mode == "fijo":
                rate = None
                amt = float(c.default_rate or 0)
            else:
                continue

            if amt <= 0 and c.calc_mode == "porcentaje":
                continue

            items.append(PayrollSlipItem(
                slip_id=slip.id, concept_id=c.id,
                concept_code=c.code, concept_name=c.name,
                type="employer_cost", rate=Decimal(str(rate)) if rate else None,
                base_amount=Decimal(str(gross)),
                amount=Decimal(str(amt)), sort_order=c.sort_order or 50,
            ))
            total_employer += amt

        # Calculate totals
        net = gross - total_ded + total_no_rem
        slip.total_remunerativo = Decimal(str(total_rem))
        slip.total_no_remunerativo = Decimal(str(total_no_rem))
        slip.total_deductions = Decimal(str(total_ded))
        slip.net_salary = Decimal(str(round(net, 2)))
        slip.total_employer_cost = Decimal(str(round(total_employer, 2)))

        db.add_all(items)
        created += 1

    db.commit()
    return {"message": f"Generated {created} payroll slips", "count": created}


# ─── Slips CRUD ────────────────────────────────────────────────────

@router.get("/slips")
def list_slips(period_id: Optional[int] = None, employee_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(PayrollSlip).options(joinedload(PayrollSlip.employee))
    if period_id:
        q = q.filter(PayrollSlip.period_id == period_id)
    if employee_id:
        q = q.filter(PayrollSlip.employee_id == employee_id)
    return [serialize_slip(s) for s in q.order_by(PayrollSlip.id).all()]


@router.get("/slips/{sid}")
def get_slip(sid: int, db: Session = Depends(get_db)):
    s = db.query(PayrollSlip).options(
        joinedload(PayrollSlip.employee),
        joinedload(PayrollSlip.items).joinedload(PayrollSlipItem.concept),
    ).filter(PayrollSlip.id == sid).first()
    if not s:
        raise HTTPException(404, "Slip not found")
    return serialize_slip(s, include_items=True)


@router.delete("/slips/{sid}", status_code=204)
def delete_slip(sid: int, db: Session = Depends(get_db)):
    s = db.query(PayrollSlip).filter(PayrollSlip.id == sid).first()
    if not s:
        raise HTTPException(404, "Slip not found")
    if s.status != "draft":
        raise HTTPException(400, "Only draft slips can be deleted")
    db.delete(s)
    db.commit()


@router.post("/slips/{sid}/items", status_code=201)
def add_slip_item(sid: int, data: SlipItemUpdate, db: Session = Depends(get_db)):
    """Add a custom item to a slip (e.g., extra bonus, deduction)."""
    s = db.query(PayrollSlip).filter(PayrollSlip.id == sid).first()
    if not s:
        raise HTTPException(404, "Slip not found")
    if s.status != "draft":
        raise HTTPException(400, "Only draft slips can be modified")

    item = PayrollSlipItem(
        slip_id=sid, concept_id=data.concept_id,
        concept_name=data.concept_name, type=data.type,
        rate=Decimal(str(data.rate)) if data.rate else None,
        base_amount=Decimal(str(data.base_amount)) if data.base_amount else None,
        amount=Decimal(str(data.amount)), sort_order=data.sort_order,
    )
    db.add(item)
    _recalc_slip(s, db)
    db.commit()
    return {"message": "Item added"}


@router.delete("/slips/{sid}/items/{iid}", status_code=204)
def remove_slip_item(sid: int, iid: int, db: Session = Depends(get_db)):
    item = db.query(PayrollSlipItem).filter(PayrollSlipItem.id == iid, PayrollSlipItem.slip_id == sid).first()
    if not item:
        raise HTTPException(404, "Item not found")
    slip = db.query(PayrollSlip).filter(PayrollSlip.id == sid).first()
    if slip and slip.status != "draft":
        raise HTTPException(400, "Only draft slips can be modified")
    db.delete(item)
    if slip:
        _recalc_slip(slip, db)
    db.commit()


def _recalc_slip(slip: PayrollSlip, db: Session):
    """Recalculate slip totals from items."""
    items = db.query(PayrollSlipItem).filter(PayrollSlipItem.slip_id == slip.id).all()
    total_rem = sum(float(i.amount or 0) for i in items if i.type == "remunerativo")
    total_no_rem = sum(float(i.amount or 0) for i in items if i.type == "no_remunerativo")
    total_ded = sum(float(i.amount or 0) for i in items if i.type == "deduccion")
    total_emp = sum(float(i.amount or 0) for i in items if i.type == "employer_cost")
    slip.total_remunerativo = Decimal(str(total_rem))
    slip.total_no_remunerativo = Decimal(str(total_no_rem))
    slip.total_deductions = Decimal(str(total_ded))
    slip.net_salary = Decimal(str(round(total_rem + total_no_rem - total_ded, 2)))
    slip.total_employer_cost = Decimal(str(round(total_emp, 2)))
