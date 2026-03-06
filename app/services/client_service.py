from sqlalchemy.orm import Session
from app.repositories.client_service import client_service_repo
from app.schemas.client_service import ClientServiceCreate, ClientServiceUpdate
from fastapi import HTTPException

class ClientServiceService:
    def get_service(self, db: Session, service_id: int):
        service = client_service_repo.get(db, service_id)
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        return service

    def get_services_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100):
        return client_service_repo.get_by_client(db, client_id=client_id, skip=skip, limit=limit)

    def get_all_services(self, db: Session, skip: int = 0, limit: int = 100):
        return client_service_repo.get_all(db, skip=skip, limit=limit)

    def create_service(self, db: Session, service_in: ClientServiceCreate):
        # Additional validation could go here (e.g., check if client exists)
        return client_service_repo.create(db, service_in=service_in)

    def update_service(self, db: Session, service_id: int, service_in: ClientServiceUpdate):
        db_service = self.get_service(db, service_id)
        return client_service_repo.update(db, db_service=db_service, service_in=service_in)

    def delete_service(self, db: Session, service_id: int):
        db_service = self.get_service(db, service_id)
        client_service_repo.delete(db, service_id)
        return {"status": "success", "message": "Service deleted successfully"}

client_service_service = ClientServiceService()
