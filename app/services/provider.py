from sqlalchemy.orm import Session
from app.repositories.provider import provider_repository
from app.schemas.provider import ProviderCreate, ProviderUpdate
from fastapi import HTTPException, status

class ProviderService:
    def create_provider(self, db: Session, provider_in: ProviderCreate):
        return provider_repository.create(db, obj_in=provider_in)

    def get_provider(self, db: Session, provider_id: int):
        provider = provider_repository.get(db, id=provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider
        
    def get_providers(self, db: Session, skip: int = 0, limit: int = 100):
        return provider_repository.get_multi(db, skip=skip, limit=limit)

    def update_provider(self, db: Session, provider_id: int, provider_in: ProviderUpdate):
        provider = provider_repository.get(db, id=provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider_repository.update(db, db_obj=provider, obj_in=provider_in)

    def delete_provider(self, db: Session, provider_id: int):
        provider = provider_repository.get(db, id=provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")
        return provider_repository.remove(db, id=provider_id)

provider_service = ProviderService()
