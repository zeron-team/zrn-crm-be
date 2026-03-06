from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CalendarEventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_date: datetime
    end_date: datetime
    related_to: Optional[str] = None
    color: Optional[str] = "#3788d8"
    client_id: Optional[int] = None
    contact_id: Optional[int] = None
    lead_id: Optional[int] = None
    status: Optional[str] = "pending"
    status_reason: Optional[str] = None
    parent_event_id: Optional[int] = None

class CalendarEventCreate(CalendarEventBase):
    pass

class CalendarEventUpdate(CalendarEventBase):
    title: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

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

class ActivityNoteCreate(BaseModel):
    content: str
