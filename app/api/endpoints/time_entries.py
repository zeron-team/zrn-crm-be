from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import cast, Date
from app.database import get_db
from app.models.time_entry import TimeEntry
from app.models.employee import Employee
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime

router = APIRouter(prefix="/time-entries", tags=["time_entries"])


@router.get("/my-status/{user_email}")
def get_my_status(user_email: str, db: Session = Depends(get_db)):
    """Get current time-tracking status for a user (matched by email or name to employee)."""
    from app.models.user import User
    # Try match by email first
    emp = db.query(Employee).filter(Employee.email == user_email).first()
    if not emp:
        # Try by matching User full_name to Employee first+last name
        user = db.query(User).filter(User.email == user_email).first()
        if user and user.full_name:
            parts = user.full_name.strip().split()
            if len(parts) >= 2:
                emp = db.query(Employee).filter(
                    Employee.first_name == parts[0],
                    Employee.last_name == " ".join(parts[1:])
                ).first()
            if not emp:
                # Try partial match
                emp = db.query(Employee).filter(
                    Employee.first_name.ilike(f"%{parts[0]}%")
                ).first()
    if not emp:
        return {"state": "no_employee", "worked_seconds": 0, "employee_id": None}

    today = date.today()
    entries = (
        db.query(TimeEntry)
        .filter(TimeEntry.employee_id == emp.id)
        .filter(cast(TimeEntry.timestamp, Date) == today)
        .order_by(TimeEntry.timestamp)
        .all()
    )

    if not entries:
        return {"state": "not_started", "worked_seconds": 0, "employee_id": emp.id,
                "employee_name": f"{emp.first_name} {emp.last_name}"}

    now = datetime.now()
    total_worked = 0.0  # seconds
    check_in_time = None
    current_state = "not_started"
    work_start = None  # timestamp when current work period started
    break_start = None
    meal_start = None
    first_check_in = None

    for e in entries:
        if e.entry_type == "check_in":
            work_start = e.timestamp
            current_state = "working"
            if first_check_in is None:
                first_check_in = e.timestamp
        elif e.entry_type == "check_out":
            if work_start:
                total_worked += (e.timestamp - work_start).total_seconds()
                work_start = None
            current_state = "out"
        elif e.entry_type == "break_start":
            if work_start:
                total_worked += (e.timestamp - work_start).total_seconds()
                work_start = None
            break_start = e.timestamp
            current_state = "break"
        elif e.entry_type == "break_end":
            break_start = None
            work_start = e.timestamp
            current_state = "working"
        elif e.entry_type == "meal_start":
            if work_start:
                total_worked += (e.timestamp - work_start).total_seconds()
                work_start = None
            meal_start = e.timestamp
            current_state = "meal"
        elif e.entry_type == "meal_end":
            meal_start = None
            work_start = e.timestamp
            current_state = "working"

    # If currently working, add time since last work_start to now
    live_since = None
    if current_state == "working" and work_start:
        total_worked += (now - work_start).total_seconds()
        live_since = work_start.isoformat()

    return {
        "state": current_state,
        "worked_seconds": int(total_worked),
        "employee_id": emp.id,
        "employee_name": f"{emp.first_name} {emp.last_name}",
        "check_in_time": first_check_in.isoformat() if first_check_in else None,
        "live_since": live_since,  # if working, timer ticks from this point
        "entries_count": len(entries),
    }


@router.get("/all-daily-summary")
def all_daily_summary(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Return daily worked hours per employee for a date range. Used for the overview chart."""
    from collections import defaultdict

    q = db.query(TimeEntry)
    if start:
        q = q.filter(cast(TimeEntry.timestamp, Date) >= start)
    if end:
        q = q.filter(cast(TimeEntry.timestamp, Date) <= end)
    entries = q.order_by(TimeEntry.timestamp).all()

    # Group entries by employee+day
    emp_days: dict[int, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for e in entries:
        day_key = e.timestamp.strftime("%Y-%m-%d")
        emp_days[e.employee_id][day_key].append(e)

    # Calculate hours per employee per day
    employees = db.query(Employee).all()
    emp_names = {e.id: f"{e.first_name} {e.last_name}" for e in employees}

    result = []
    all_dates = set()
    emp_data: dict[int, dict[str, float]] = {}

    for emp_id, days in emp_days.items():
        emp_data[emp_id] = {}
        for day_key, day_entries in days.items():
            all_dates.add(day_key)
            work_start = None
            worked = 0.0
            for entry in sorted(day_entries, key=lambda x: x.timestamp):
                if entry.entry_type == "check_in":
                    work_start = entry.timestamp
                elif entry.entry_type in ("check_out", "break_start", "meal_start"):
                    if work_start:
                        worked += (entry.timestamp - work_start).total_seconds()
                        work_start = None
                elif entry.entry_type in ("break_end", "meal_end"):
                    work_start = entry.timestamp
            emp_data[emp_id][day_key] = round(worked / 3600, 2)

    # Build chart-friendly data: [{date, emp1_name, emp1_hours, emp2_name, emp2_hours, ...}]
    chart_data = []
    for d in sorted(all_dates):
        row: dict = {"date": d}
        for emp_id in emp_data:
            prefix = f"e{emp_id}"
            row[f"{prefix}_hours"] = emp_data[emp_id].get(d, 0)
            row[f"{prefix}_name"] = emp_names.get(emp_id, f"Emp {emp_id}")
        chart_data.append(row)

    emp_meta = [{"id": eid, "prefix": f"e{eid}", "name": emp_names.get(eid, f"Emp {eid}")}
                for eid in emp_data]

    return {"chart": chart_data, "employees": emp_meta}


class TimeEntryCreate(BaseModel):
    employee_id: int
    entry_type: str  # check_in, check_out, break_start, break_end, meal_start, meal_end
    timestamp: Optional[datetime] = None
    notes: Optional[str] = None
    ip_address: Optional[str] = None


def serialize_entry(e: TimeEntry) -> dict:
    emp_name = None
    if e.employee:
        emp_name = f"{e.employee.first_name} {e.employee.last_name}"
    return {
        "id": e.id,
        "employee_id": e.employee_id,
        "employee_name": emp_name,
        "entry_type": e.entry_type,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "notes": e.notes,
        "ip_address": e.ip_address,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


@router.get("/")
def list_time_entries(
    employee_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
):
    q = db.query(TimeEntry)
    if employee_id:
        q = q.filter(TimeEntry.employee_id == employee_id)
    if date_from:
        q = q.filter(cast(TimeEntry.timestamp, Date) >= date_from)
    if date_to:
        q = q.filter(cast(TimeEntry.timestamp, Date) <= date_to)
    entries = q.order_by(TimeEntry.timestamp.desc()).all()
    return [serialize_entry(e) for e in entries]


@router.post("/", status_code=201)
def create_time_entry(data: TimeEntryCreate, db: Session = Depends(get_db)):
    # Validate employee exists
    emp = db.query(Employee).filter(Employee.id == data.employee_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    valid_types = {"check_in", "check_out", "break_start", "break_end", "meal_start", "meal_end"}
    if data.entry_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid entry_type. Must be one of: {valid_types}")

    entry = TimeEntry(
        employee_id=data.employee_id,
        entry_type=data.entry_type,
        timestamp=data.timestamp or datetime.now(),
        notes=data.notes,
        ip_address=data.ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return serialize_entry(entry)


@router.delete("/{entry_id}", status_code=204)
def delete_time_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(TimeEntry).filter(TimeEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    db.delete(entry)
    db.commit()


@router.get("/today/{employee_id}")
def get_today_entries(employee_id: int, db: Session = Depends(get_db)):
    """Get all time entries for an employee today."""
    today = date.today()
    entries = (
        db.query(TimeEntry)
        .filter(TimeEntry.employee_id == employee_id)
        .filter(cast(TimeEntry.timestamp, Date) == today)
        .order_by(TimeEntry.timestamp)
        .all()
    )
    return [serialize_entry(e) for e in entries]
