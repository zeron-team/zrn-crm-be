from sqlalchemy.orm import Session
from app.repositories.activity_note import activity_note_repository
from fastapi import HTTPException

class ActivityNoteService:
    def get_notes(self, db: Session, event_id: int):
        return activity_note_repository.get_by_event(db, event_id=event_id)

    def add_note(self, db: Session, event_id: int, content: str):
        return activity_note_repository.create(db, event_id=event_id, content=content)

    def update_note(self, db: Session, note_id: int, content: str):
        note = activity_note_repository.update(db, note_id=note_id, content=content)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note

    def delete_note(self, db: Session, note_id: int):
        note = activity_note_repository.remove(db, note_id=note_id)
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
        return note

activity_note_service = ActivityNoteService()
