from sqlalchemy.orm import Session
from app.repositories.client import client_repository
from app.schemas.client import ClientCreate, ClientUpdate
from fastapi import HTTPException, status

class ClientService:
    def create_client(self, db: Session, client_in: ClientCreate):
        return client_repository.create(db, obj_in=client_in)

    def get_client(self, db: Session, client_id: int):
        client = client_repository.get(db, id=client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client
        
    def get_clients(self, db: Session, skip: int = 0, limit: int = 100):
        return client_repository.get_multi(db, skip=skip, limit=limit)

    def update_client(self, db: Session, client_id: int, client_in: ClientUpdate):
        client = client_repository.get(db, id=client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client_repository.update(db, db_obj=client, obj_in=client_in)

    def delete_client(self, db: Session, client_id: int):
        client = client_repository.get(db, id=client_id)
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        return client_repository.remove(db, id=client_id)

client_service = ClientService()
