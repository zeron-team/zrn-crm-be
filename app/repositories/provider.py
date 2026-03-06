from sqlalchemy.orm import Session
from app.models.provider import Provider
from app.schemas.provider import ProviderCreate, ProviderUpdate

class ProviderRepository:
    def get(self, db: Session, id: int) -> Provider | None:
        return db.query(Provider).filter(Provider.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Provider]:
        return db.query(Provider).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProviderCreate) -> Provider:
        db_obj = Provider(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Provider, obj_in: ProviderUpdate) -> Provider:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Provider:
        obj = db.query(Provider).get(id)
        db.delete(obj)
        db.commit()
        return obj

provider_repository = ProviderRepository()
