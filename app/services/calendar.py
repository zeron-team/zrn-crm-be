from sqlalchemy.orm import Session
from app.repositories.calendar import calendar_event_repository
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from app.models.calendar import CalendarEvent
from datetime import datetime, time, date
import calendar
from typing import List
from fastapi import HTTPException
from app.models.provider_service import ProviderService

class CalendarEventService:
    def create_event(self, db: Session, event_in: CalendarEventCreate):
        first_event = calendar_event_repository.create(db, obj_in=event_in)

        # Generate recurring copies if applicable
        if event_in.is_recurring and event_in.recurrence_pattern and event_in.recurrence_end_date:
            from dateutil.relativedelta import relativedelta
            from copy import deepcopy

            pattern = event_in.recurrence_pattern
            end_limit = event_in.recurrence_end_date  # date object
            
            orig_start = event_in.start_date  # datetime
            orig_end = event_in.end_date      # datetime
            duration = orig_end - orig_start

            deltas = {
                "daily": relativedelta(days=1),
                "weekly": relativedelta(weeks=1),
                "biweekly": relativedelta(weeks=2),
                "monthly": relativedelta(months=1),
            }
            delta = deltas.get(pattern)
            if delta:
                current_start = orig_start + delta
                max_occurrences = 365  # safety limit
                count = 0
                while current_start.date() <= end_limit and count < max_occurrences:
                    clone_data = event_in.model_copy()
                    clone_data.start_date = current_start
                    clone_data.end_date = current_start + duration
                    clone_data.parent_event_id = first_event.id
                    calendar_event_repository.create(db, obj_in=clone_data)
                    current_start = current_start + delta
                    count += 1

        return first_event

    def get_event(self, db: Session, event_id: int):
        event = calendar_event_repository.get(db, id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
        
    def get_events(self, db: Session, skip: int = 0, limit: int = 100):
        db_events = calendar_event_repository.get_multi(db, skip=skip, limit=limit)
        events_list = [e for e in db_events]
        
        provider_services = db.query(ProviderService).filter(ProviderService.status == "Active").all()
        for ps in provider_services:
            if not ps.expiration_date: continue
            
            occurrences = 1
            interval_months = 0
            
            if ps.billing_cycle == "Monthly":
                occurrences = 24
                interval_months = 1
            elif ps.billing_cycle == "Bimonthly":
                occurrences = 12
                interval_months = 2
            elif ps.billing_cycle == "Yearly":
                occurrences = 5
                interval_months = 12
                
            for i in range(occurrences):
                month = ps.expiration_date.month + (i * interval_months) - 1
                year = ps.expiration_date.year + month // 12
                month = month % 12 + 1
                day = min(ps.expiration_date.day, calendar.monthrange(year, month)[1])
                future_date = date(year, month, day)
                
                exp_datetime = datetime.combine(future_date, time(9, 0))
                
                class VirtualEvent:
                    id = -(ps.id * 1000 + i) # Unique negative ID per occurrence
                    title = f"Renew: {ps.name}"
                    description = f"Cost: {ps.currency} {ps.cost_price}"
                    start_date = exp_datetime
                    end_date = exp_datetime
                    related_to = "Renewal"
                    color = "#ef4444" # Red
                    client_id = None
                    contact_id = None
                    contact_ids = []
                    lead_id = None
                    status = "pending"
                    status_reason = None
                    parent_event_id = None
                    call_url = None
                    is_recurring = False
                    recurrence_pattern = None
                    recurrence_end_date = None
                    project_id = None
                    notes = []
                    contacts = []
                events_list.append(VirtualEvent())
                
        return events_list

    def update_event(self, db: Session, event_id: int, event_in: CalendarEventUpdate):
        event = calendar_event_repository.get(db, id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        updated = calendar_event_repository.update(db, db_obj=event, obj_in=event_in)

        # Handle recurrence on update
        if event_in.is_recurring and event_in.recurrence_pattern and event_in.recurrence_end_date:
            from dateutil.relativedelta import relativedelta

            # Remove old child events for this parent
            db.query(CalendarEvent).filter(
                CalendarEvent.parent_event_id == event_id
            ).delete(synchronize_session=False)
            db.commit()

            pattern = event_in.recurrence_pattern
            end_limit = event_in.recurrence_end_date

            orig_start = updated.start_date
            orig_end = updated.end_date
            duration = orig_end - orig_start

            deltas = {
                "daily": relativedelta(days=1),
                "weekly": relativedelta(weeks=1),
                "biweekly": relativedelta(weeks=2),
                "monthly": relativedelta(months=1),
            }
            delta = deltas.get(pattern)
            if delta:
                current_start = orig_start + delta
                max_occurrences = 365
                count = 0
                while current_start.date() <= end_limit and count < max_occurrences:
                    child = CalendarEvent(
                        title=updated.title,
                        description=updated.description,
                        start_date=current_start,
                        end_date=current_start + duration,
                        related_to=updated.related_to,
                        color=updated.color,
                        client_id=updated.client_id,
                        contact_id=updated.contact_id,
                        lead_id=updated.lead_id,
                        status="pending",
                        call_url=updated.call_url,
                        is_recurring=False,
                        recurrence_pattern=None,
                        recurrence_end_date=None,
                        project_id=updated.project_id,
                        parent_event_id=event_id,
                    )
                    db.add(child)
                    current_start = current_start + delta
                    count += 1
                db.commit()

        return updated

    def delete_event(self, db: Session, event_id: int):
        event = calendar_event_repository.get(db, id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return calendar_event_repository.remove(db, id=event_id)

calendar_event_service = CalendarEventService()
