from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate, CalendarEventResponse, ActivityNoteCreate, ActivityNoteResponse
from app.services.calendar import calendar_event_service
from app.services.activity_note import activity_note_service

router = APIRouter()

@router.post("/", response_model=CalendarEventResponse)
def create_event(event_in: CalendarEventCreate, db: Session = Depends(get_db)):
    return calendar_event_service.create_event(db, event_in=event_in)

@router.get("/", response_model=List[CalendarEventResponse])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return calendar_event_service.get_events(db, skip=skip, limit=limit)

@router.get("/{event_id}", response_model=CalendarEventResponse)
def read_event(event_id: int, db: Session = Depends(get_db)):
    return calendar_event_service.get_event(db, event_id=event_id)

@router.put("/{event_id}", response_model=CalendarEventResponse)
def update_event(event_id: int, event_in: CalendarEventUpdate, db: Session = Depends(get_db)):
    return calendar_event_service.update_event(db, event_id=event_id, event_in=event_in)

@router.delete("/{event_id}", response_model=CalendarEventResponse)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    return calendar_event_service.delete_event(db, event_id=event_id)

# --- Activity Notes ---

@router.get("/{event_id}/notes", response_model=List[ActivityNoteResponse])
def get_event_notes(event_id: int, db: Session = Depends(get_db)):
    return activity_note_service.get_notes(db, event_id=event_id)

@router.post("/{event_id}/notes", response_model=ActivityNoteResponse)
def add_event_note(event_id: int, note_in: ActivityNoteCreate, db: Session = Depends(get_db)):
    return activity_note_service.add_note(db, event_id=event_id, content=note_in.content)

@router.put("/{event_id}/notes/{note_id}", response_model=ActivityNoteResponse)
def update_event_note(event_id: int, note_id: int, note_in: ActivityNoteCreate, db: Session = Depends(get_db)):
    return activity_note_service.update_note(db, note_id=note_id, content=note_in.content)

@router.delete("/{event_id}/notes/{note_id}", response_model=ActivityNoteResponse)
def delete_event_note(event_id: int, note_id: int, db: Session = Depends(get_db)):
    return activity_note_service.delete_note(db, note_id=note_id)
