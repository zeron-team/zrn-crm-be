from sqlalchemy.orm import Session
from app.repositories.calendar import calendar_event_repository
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate
from sqlalchemy.orm import Session
from datetime import datetime, time, date
import calendar
from typing import List
from fastapi import HTTPException
from app.models.provider_service import ProviderService

class CalendarEventService:
    def create_event(self, db: Session, event_in: CalendarEventCreate):
        return calendar_event_repository.create(db, obj_in=event_in)

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
                    lead_id = None
                    status = "pending"
                    status_reason = None
                    parent_event_id = None
                    call_url = None
                    is_recurring = False
                    recurrence_pattern = None
                    project_id = None
                    notes = []
                    
                events_list.append(VirtualEvent())
                
        return events_list

    def update_event(self, db: Session, event_id: int, event_in: CalendarEventUpdate):
        event = calendar_event_repository.get(db, id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return calendar_event_repository.update(db, db_obj=event, obj_in=event_in)

    def delete_event(self, db: Session, event_id: int):
        event = calendar_event_repository.get(db, id=event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return calendar_event_repository.remove(db, id=event_id)

calendar_event_service = CalendarEventService()
