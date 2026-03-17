from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

class CalendarEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    related_to: Optional[str] = None
    color: Optional[str] = "#3788d8"
    client_id: Optional[int] = None
    contact_id: Optional[int] = None  # legacy single contact (kept for compat)
    contact_ids: Optional[List[int]] = None  # multiple contacts
    lead_id: Optional[int] = None
    status: Optional[str] = "pending"
    status_reason: Optional[str] = None
    parent_event_id: Optional[int] = None
    call_url: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurrence_pattern: Optional[str] = None
    recurrence_end_date: Optional[date] = None
    project_id: Optional[int] = None

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventUpdate(CalendarEventBase):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class ContactMini(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    position: Optional[str] = None

    class Config:
        from_attributes = True

class ActivityNoteResponse(BaseModel):
    id: int
    event_id: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class CalendarEventInDBBase(CalendarEventBase):
    id: int

    class Config:
        from_attributes = True

class CalendarEventResponse(CalendarEventInDBBase):
    notes: List[ActivityNoteResponse] = []
    contacts: List[ContactMini] = []

class ActivityNoteCreate(BaseModel):
    content: str
