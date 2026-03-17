from sqlalchemy.orm import Session
from app.models.calendar import CalendarEvent, calendar_event_contacts
from app.models.contact import Contact
from app.schemas.calendar import CalendarEventCreate, CalendarEventUpdate

class CalendarEventRepository:
    def get(self, db: Session, id: int) -> CalendarEvent | None:
        return db.query(CalendarEvent).filter(CalendarEvent.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[CalendarEvent]:
        return db.query(CalendarEvent).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CalendarEventCreate) -> CalendarEvent:
        data = obj_in.model_dump(exclude={"contact_ids"})
        contact_ids = obj_in.contact_ids or []
        # Legacy compat: if contact_ids provided, set contact_id to first one
        if contact_ids and not data.get("contact_id"):
            data["contact_id"] = contact_ids[0]
        db_obj = CalendarEvent(**data)
        db.add(db_obj)
        db.flush()
        # Sync M2M contacts
        if contact_ids:
            contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()
            db_obj.contacts = contacts
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: CalendarEvent, obj_in: CalendarEventUpdate) -> CalendarEvent:
        update_data = obj_in.model_dump(exclude_unset=True, exclude={"contact_ids"})
        contact_ids = obj_in.contact_ids
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        # Sync M2M contacts if provided
        if contact_ids is not None:
            contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all() if contact_ids else []
            db_obj.contacts = contacts
            # Legacy compat
            db_obj.contact_id = contact_ids[0] if contact_ids else None
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
