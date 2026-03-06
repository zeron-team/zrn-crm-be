from sqlalchemy.orm import Session
from app.models.client_service import ClientService
from app.schemas.client_service import ClientServiceCreate, ClientServiceUpdate

class ClientServiceRepository:
    def get(self, db: Session, service_id: int):
        return db.query(ClientService).filter(ClientService.id == service_id).first()

    def get_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100):
        return db.query(ClientService).filter(ClientService.client_id == client_id).offset(skip).limit(limit).all()

    def get_all(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(ClientService).offset(skip).limit(limit).all()

    def create(self, db: Session, service_in: ClientServiceCreate):
        db_service = ClientService(
            client_id=service_in.client_id,
            product_id=service_in.product_id,
            name=service_in.name,
            status=service_in.status,
            billing_cycle=service_in.billing_cycle,
            characteristics=service_in.characteristics,
            start_date=service_in.start_date,
            end_date=service_in.end_date
        )
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        return db_service

    def update(self, db: Session, db_service: ClientService, service_in: ClientServiceUpdate):
        update_data = service_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_service, field, value)
        
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        return db_service

    def delete(self, db: Session, service_id: int):
        db_service = db.query(ClientService).filter(ClientService.id == service_id).first()
        if db_service:
            db.delete(db_service)
            db.commit()
            return True
        return False

client_service_repo = ClientServiceRepository()
