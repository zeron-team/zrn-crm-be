from sqlalchemy.orm import Session
from app.models.activity_note import ActivityNote

class ActivityNoteRepository:
    def get_by_event(self, db: Session, event_id: int) -> list[ActivityNote]:
        return db.query(ActivityNote).filter(ActivityNote.event_id == event_id).order_by(ActivityNote.created_at.desc()).all()

    def create(self, db: Session, event_id: int, content: str) -> ActivityNote:
        db_obj = ActivityNote(event_id=event_id, content=content)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, note_id: int, content: str) -> ActivityNote | None:
        obj = db.query(ActivityNote).filter(ActivityNote.id == note_id).first()
        if obj:
            obj.content = content
            db.commit()
            db.refresh(obj)
        return obj

    def remove(self, db: Session, note_id: int) -> ActivityNote | None:
        obj = db.query(ActivityNote).filter(ActivityNote.id == note_id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

activity_note_repository = ActivityNoteRepository()
