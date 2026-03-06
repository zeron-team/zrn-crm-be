from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from app.database import get_db
from app.models.employee import Employee
from app.models.time_entry import TimeEntry
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeCreate(BaseModel):
    legajo: str
    first_name: str
    last_name: str
    dni: str
    user_id: Optional[int] = None
    cuil: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    marital_status: Optional[str] = None
    nationality: Optional[str] = "Argentina"
    photo_url: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    hire_date: Optional[date] = None
    termination_date: Optional[date] = None
    department: Optional[str] = None
    position: Optional[str] = None
    supervisor_id: Optional[int] = None
    contract_type: Optional[str] = "permanent"
    billing_type: Optional[str] = "payroll"
    work_schedule: Optional[str] = "full_time"
    weekly_hours: Optional[int] = 45
    obra_social: Optional[str] = None
    obra_social_plan: Optional[str] = None
    obra_social_number: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    bank_name: Optional[str] = None
    bank_cbu: Optional[str] = None
    salary: Optional[float] = None
    salary_currency: Optional[str] = "ARS"
    notes: Optional[str] = None
    is_active: Optional[bool] = True


class EmployeeUpdate(EmployeeCreate):
    legajo: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    dni: Optional[str] = None


def serialize_employee(emp: Employee) -> dict:
    supervisor_name = None
    if emp.supervisor:
        supervisor_name = f"{emp.supervisor.first_name} {emp.supervisor.last_name}"

    # Check completeness: required fields for a full legajo
    required_fields = [emp.legajo, emp.dni, emp.first_name, emp.last_name,
                       emp.department, emp.position, emp.hire_date, emp.contract_type]
    data_complete = all(f is not None and f != '' for f in required_fields)

    return {
        "id": emp.id,
        "user_id": emp.user_id,
        "legajo": emp.legajo,
        "first_name": emp.first_name,
        "last_name": emp.last_name,
        "full_name": f"{emp.first_name} {emp.last_name}",
        "dni": emp.dni,
        "cuil": emp.cuil,
        "birth_date": str(emp.birth_date) if emp.birth_date else None,
        "gender": emp.gender,
        "marital_status": emp.marital_status,
        "nationality": emp.nationality,
        "photo_url": emp.photo_url,
        "phone": emp.phone,
        "email": emp.email,
        "address": emp.address,
        "city": emp.city,
        "province": emp.province,
        "postal_code": emp.postal_code,
        "hire_date": str(emp.hire_date) if emp.hire_date else None,
        "termination_date": str(emp.termination_date) if emp.termination_date else None,
        "department": emp.department,
        "position": emp.position,
        "supervisor_id": emp.supervisor_id,
        "supervisor_name": supervisor_name,
        "contract_type": emp.contract_type,
        "billing_type": emp.billing_type,
        "work_schedule": emp.work_schedule,
        "weekly_hours": emp.weekly_hours,
        "obra_social": emp.obra_social,
        "obra_social_plan": emp.obra_social_plan,
        "obra_social_number": emp.obra_social_number,
        "emergency_contact": emp.emergency_contact,
        "emergency_phone": emp.emergency_phone,
        "bank_name": emp.bank_name,
        "bank_cbu": emp.bank_cbu,
        "salary": float(emp.salary) if emp.salary else None,
        "salary_currency": emp.salary_currency,
        "notes": emp.notes,
        "is_active": emp.is_active,
        "data_complete": data_complete,
        "created_at": emp.created_at.isoformat() if emp.created_at else None,
        "updated_at": emp.updated_at.isoformat() if emp.updated_at else None,
    }


@router.get("/unlinked-users")
def get_unlinked_users(db: Session = Depends(get_db)):
    """Return users with 'empleado' role who don't have a matching Employee record."""
    from app.models.user import User
    empleado_users = db.query(User).filter(User.role.contains("empleado")).all()
    all_employees = db.query(Employee).all()

    # Build set of linked user_ids (definitive link)
    linked_user_ids = {e.user_id for e in all_employees if e.user_id}
    # Also fallback to email and full name matching for legacy records without user_id
    existing_emails = {e.email.lower() for e in all_employees if e.email}
    existing_names = {f"{e.first_name} {e.last_name}".strip().lower() for e in all_employees if e.first_name and e.last_name}

    unlinked = []
    for u in empleado_users:
        # Skip if user_id is linked (definitive)
        if u.id in linked_user_ids:
            continue
        # Skip if email matches any employee
        if u.email and u.email.lower() in existing_emails:
            continue
        # Skip if full_name matches any employee
        if u.full_name and u.full_name.strip().lower() in existing_names:
            continue
        # Split full_name into first_name and last_name
        parts = (u.full_name or "").strip().split(" ", 1)
        fname = parts[0] if parts else ""
        lname = parts[1] if len(parts) > 1 else ""
        unlinked.append({
            "id": None,
            "user_id": u.id,
            "full_name": u.full_name or u.email,
            "first_name": fname,
            "last_name": lname,
            "email": u.email,
            "is_active": u.is_active,
            "data_complete": False,
            "department": None,
            "position": None,
            "legajo": None,
            "contract_type": None,
            "_is_stub": True,
        })
    return unlinked


@router.get("/")
def list_employees(
    department: Optional[str] = None,
    contract_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Employee)
    if department:
        q = q.filter(Employee.department == department)
    if contract_type:
        q = q.filter(Employee.contract_type == contract_type)
    if is_active is not None:
        q = q.filter(Employee.is_active == is_active)
    employees = q.order_by(Employee.last_name, Employee.first_name).all()
    return [serialize_employee(e) for e in employees]


@router.post("/", status_code=201)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db)):
    # Prevent duplicate user_id link
    if data.user_id:
        existing = db.query(Employee).filter(Employee.user_id == data.user_id).first()
        if existing:
            raise HTTPException(400, f"User {data.user_id} already linked to employee {existing.legajo}")
    emp = Employee(**data.model_dump(exclude_none=False))
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return serialize_employee(emp)


@router.get("/{employee_id}")
def get_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return serialize_employee(emp)


@router.put("/{employee_id}")
def update_employee(employee_id: int, data: EmployeeUpdate, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(emp, key, value)
    db.commit()
    db.refresh(emp)
    return serialize_employee(emp)


@router.delete("/{employee_id}", status_code=204)
def delete_employee(employee_id: int, db: Session = Depends(get_db)):
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(emp)
    db.commit()


@router.get("/{employee_id}/time-summary")
def get_time_summary(
    employee_id: int,
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Calculate worked days and hours for an employee within a date range."""
    emp = db.query(Employee).filter(Employee.id == employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    q = db.query(TimeEntry).filter(TimeEntry.employee_id == employee_id)
    if start:
        q = q.filter(cast(TimeEntry.timestamp, Date) >= start)
    if end:
        q = q.filter(cast(TimeEntry.timestamp, Date) <= end)

    entries = q.order_by(TimeEntry.timestamp).all()

    # Group by day
    days: dict[str, list] = {}
    for e in entries:
        day_key = e.timestamp.strftime("%Y-%m-%d")
        days.setdefault(day_key, []).append(e)

    total_worked_minutes = 0
    day_details = []

    for day_key, day_entries in sorted(days.items()):
        check_in = None
        break_minutes = 0
        meal_minutes = 0
        break_start = None
        meal_start = None
        worked_minutes = 0

        for entry in sorted(day_entries, key=lambda x: x.timestamp):
            if entry.entry_type == "check_in":
                check_in = entry.timestamp
            elif entry.entry_type == "check_out" and check_in:
                worked_minutes += (entry.timestamp - check_in).total_seconds() / 60
                check_in = None
            elif entry.entry_type == "break_start":
                break_start = entry.timestamp
            elif entry.entry_type == "break_end" and break_start:
                break_minutes += (entry.timestamp - break_start).total_seconds() / 60
                break_start = None
            elif entry.entry_type == "meal_start":
                meal_start = entry.timestamp
            elif entry.entry_type == "meal_end" and meal_start:
                meal_minutes += (entry.timestamp - meal_start).total_seconds() / 60
                meal_start = None

        net_minutes = max(0, worked_minutes - break_minutes - meal_minutes)
        total_worked_minutes += net_minutes

        day_details.append({
            "date": day_key,
            "worked_hours": round(net_minutes / 60, 2),
            "break_hours": round(break_minutes / 60, 2),
            "meal_hours": round(meal_minutes / 60, 2),
            "entries": len(day_entries),
        })

    total_days = len(days)
    total_hours = round(total_worked_minutes / 60, 2)
    avg_hours = round(total_hours / total_days, 2) if total_days > 0 else 0

    return {
        "employee_id": employee_id,
        "total_days": total_days,
        "total_hours": total_hours,
        "avg_hours_per_day": avg_hours,
        "days": day_details,
    }
