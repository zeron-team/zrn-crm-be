"""Notifications aggregation — counts for all notification types."""
from datetime import datetime, timezone, date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, cast, Date as SADate
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.calendar import CalendarEvent
from app.models.note import Note
from app.models.project import Sprint

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/counts")
def notification_counts(user_id: int = Query(None), db: Session = Depends(get_db)):
    """Return pending/urgent counts for each notification channel."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    week_ahead = today + timedelta(days=7)

    # 1. CITAS — calendar events with status pending/postponed, starting today or before tomorrow
    citas = db.query(func.count(CalendarEvent.id)).filter(
        CalendarEvent.status.in_(["pending", "postponed"]),
        cast(CalendarEvent.start_date, SADate) <= tomorrow
    ).scalar() or 0

    # 2. VENCIMIENTOS — quote installments pending within 7 days
    vencimientos = 0
    try:
        from app.models.quote_installment import QuoteInstallment
        vencimientos = db.query(func.count(QuoteInstallment.id)).filter(
            QuoteInstallment.status == 'pending',
            QuoteInstallment.due_date <= week_ahead
        ).scalar() or 0
    except Exception:
        pass

    # 3. MAILS — handled client-side, return 0 placeholder
    mails = 0

    # 4. SPRINTS — ending within 3 days or already past end_date while still active
    sprints = db.query(func.count(Sprint.id)).filter(
        Sprint.status == 'active',
        Sprint.end_date != None,
        Sprint.end_date <= today + timedelta(days=3)
    ).scalar() or 0

    # 5. WHATSAPP — handled client-side, return 0 placeholder
    whatsapp = 0

    # 6. NOTAS — assigned to user
    notas = 0
    if user_id:
        notas = db.query(func.count(Note.id)).filter(
            Note.assigned_to == user_id
        ).scalar() or 0

    return {
        "citas": citas,
        "vencimientos": vencimientos,
        "mails": mails,
        "sprints": sprints,
        "whatsapp": whatsapp,
        "notas": notas,
    }
