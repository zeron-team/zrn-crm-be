from sqlalchemy.orm import Session
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate

class ClientRepository:
    def get(self, db: Session, id: int) -> Client | None:
        return db.query(Client).filter(Client.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Client]:
        return db.query(Client).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ClientCreate) -> Client:
        db_obj = Client(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Client, obj_in: ClientUpdate) -> Client:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Client:
        obj = db.query(Client).get(id)
        db.delete(obj)
        db.commit()
        return obj

client_repository = ClientRepository()
