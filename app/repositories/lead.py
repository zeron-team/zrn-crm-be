from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate

class LeadRepository:
    def get(self, db: Session, id: int) -> Lead | None:
        return db.query(Lead).filter(Lead.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Lead]:
        return db.query(Lead).order_by(Lead.id.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: LeadCreate) -> Lead:
        db_obj = Lead(**obj_in.dict())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Lead, obj_in: LeadUpdate | dict) -> Lead:
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
                
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> Lead:
        obj = db.query(Lead).get(id)
        db.delete(obj)
        db.commit()
        return obj

lead_repository = LeadRepository()
