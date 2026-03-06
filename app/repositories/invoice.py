from sqlalchemy.orm import Session
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceStatusCreate, InvoiceStatusUpdate

class InvoiceRepository:
    def get(self, db: Session, id: int) -> Invoice | None:
        return db.query(Invoice).filter(Invoice.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Invoice]:
        return db.query(Invoice).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: InvoiceCreate) -> Invoice:
        db_obj = Invoice(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Invoice, obj_in: InvoiceUpdate) -> Invoice:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Invoice:
        obj = db.query(Invoice).get(id)
        db.delete(obj)
        db.commit()
        return obj

class InvoiceStatusRepository:
    def get(self, db: Session, id: int) -> InvoiceStatus | None:
        return db.query(InvoiceStatus).filter(InvoiceStatus.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[InvoiceStatus]:
        return db.query(InvoiceStatus).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: InvoiceStatusCreate) -> InvoiceStatus:
        db_obj = InvoiceStatus(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: InvoiceStatus, obj_in: InvoiceStatusUpdate) -> InvoiceStatus:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> InvoiceStatus:
        obj = db.query(InvoiceStatus).get(id)
        db.delete(obj)
        db.commit()
        return obj

invoice_repository = InvoiceRepository()
invoice_status_repository = InvoiceStatusRepository()
