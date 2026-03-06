from sqlalchemy.orm import Session
from app.models.calendar import CalendarEvent
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

class CalendarEventRepository:
    def get(self, db: Session, id: int) -> CalendarEvent | None:
        return db.query(CalendarEvent).filter(CalendarEvent.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[CalendarEvent]:
        return db.query(CalendarEvent).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CalendarEventCreate) -> CalendarEvent:
        db_obj = CalendarEvent(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: CalendarEvent, obj_in: CalendarEventUpdate) -> CalendarEvent:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> CalendarEvent:
        obj = db.query(CalendarEvent).get(id)
        db.delete(obj)
        db.commit()
        return obj

calendar_event_repository = CalendarEventRepository()
