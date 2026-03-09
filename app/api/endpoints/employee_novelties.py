"""Employee Novelties CRUD — leaves, absences, vacations, overtime, medical."""
from typing import Optional
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee_novelty import EmployeeNovelty
from app.models.employee import Employee
from app.models.user import User
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/employee-novelties", tags=["employee-novelties"])

NOVELTY_TYPES = [
    "vacation", "medical_leave", "personal_leave", "absence",
    "overtime", "late_arrival", "maternity", "paternity",
    "study_leave", "bereavement", "compensatory", "other"
]

# ── Schemas ──
class NoveltyCreate(BaseModel):
    employee_id: int
    type: str
    start_date: date
    end_date: date
    days_count: float = 1
    reason: Optional[str] = None
    notes: Optional[str] = None

class NoveltyUpdate(BaseModel):
    type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days_count: Optional[float] = None
    reason: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

class StatusUpdate(BaseModel):
    status: str  # approved, rejected, cancelled


def _serialize(n, db):
    emp = db.query(Employee).get(n.employee_id)
    emp_name = f"{emp.last_name}, {emp.first_name}" if emp else "—"
    requester = db.query(User).get(n.requested_by) if n.requested_by else None
    approver = db.query(User).get(n.approved_by) if n.approved_by else None
    return {
        "id": n.id,
        "employee_id": n.employee_id,
        "employee_name": emp_name,
        "employee_legajo": emp.legajo if emp else None,
        "employee_department": emp.department if emp else None,
        "type": n.type,
        "status": n.status,
        "start_date": n.start_date.isoformat() if n.start_date else None,
        "end_date": n.end_date.isoformat() if n.end_date else None,
        "days_count": n.days_count,
        "reason": n.reason,
        "notes": n.notes,
        "attachment_url": n.attachment_url,
        "requested_by": n.requested_by,
        "requested_by_name": requester.full_name or requester.username if requester else None,
        "approved_by": n.approved_by,
        "approved_by_name": approver.full_name or approver.username if approver else None,
        "approved_at": n.approved_at.isoformat() if n.approved_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("")
def list_novelties(
    employee_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(EmployeeNovelty)
    if employee_id:
        q = q.filter(EmployeeNovelty.employee_id == employee_id)
    if type:
        q = q.filter(EmployeeNovelty.type == type)
    if status:
        q = q.filter(EmployeeNovelty.status == status)
    items = q.order_by(desc(EmployeeNovelty.start_date)).all()
    return [_serialize(i, db) for i in items]


@router.get("/types")
def get_types():
    return NOVELTY_TYPES


@router.get("/summary")
def get_summary(
    year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Summary counts by type and status."""
    from sqlalchemy import func, extract
    q = db.query(EmployeeNovelty)
    if year:
        q = q.filter(extract('year', EmployeeNovelty.start_date) == year)

    by_type = {}
    by_status = {"pending": 0, "approved": 0, "rejected": 0, "cancelled": 0}
    total_days = 0
    items = q.all()
    for i in items:
        by_type[i.type] = by_type.get(i.type, 0) + 1
        by_status[i.status] = by_status.get(i.status, 0) + 1
        if i.status == "approved":
            total_days += i.days_count or 0
    return {"total": len(items), "by_type": by_type, "by_status": by_status, "approved_days": total_days}


@router.post("", status_code=201)
def create_novelty(data: NoveltyCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    emp = db.query(Employee).get(data.employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    nov = EmployeeNovelty(
        **data.model_dump(),
        requested_by=current_user.id,
    )
    db.add(nov)
    db.commit()
    db.refresh(nov)
    return _serialize(nov, db)


@router.get("/{novelty_id}")
def get_novelty(novelty_id: int, db: Session = Depends(get_db)):
    nov = db.query(EmployeeNovelty).get(novelty_id)
    if not nov:
        raise HTTPException(404, "Novelty not found")
    return _serialize(nov, db)


@router.put("/{novelty_id}")
def update_novelty(novelty_id: int, data: NoveltyUpdate, db: Session = Depends(get_db)):
    nov = db.query(EmployeeNovelty).get(novelty_id)
    if not nov:
        raise HTTPException(404, "Novelty not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(nov, k, v)
    nov.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(nov)
    return _serialize(nov, db)


@router.patch("/{novelty_id}/status")
def change_status(novelty_id: int, data: StatusUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    nov = db.query(EmployeeNovelty).get(novelty_id)
    if not nov:
        raise HTTPException(404, "Novelty not found")
    nov.status = data.status
    if data.status == "approved":
        nov.approved_by = current_user.id
        nov.approved_at = datetime.now(timezone.utc)
    nov.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(nov)
    return _serialize(nov, db)


@router.delete("/{novelty_id}")
def delete_novelty(novelty_id: int, db: Session = Depends(get_db)):
    nov = db.query(EmployeeNovelty).get(novelty_id)
    if not nov:
        raise HTTPException(404, "Novelty not found")
    db.delete(nov)
    db.commit()
    return {"ok": True}
