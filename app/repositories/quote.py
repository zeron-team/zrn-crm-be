from sqlalchemy.orm import Session
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.schemas.quote import QuoteCreate, QuoteUpdate
import uuid

class QuoteRepository:
    def get(self, db: Session, id: int):
        return db.query(Quote).filter(Quote.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Quote).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: QuoteCreate):
        # Generate a unique quote number (or sequential if preferred, using UUID for simplicity/safety)
        quote_number = f"QT-{uuid.uuid4().hex[:8].upper()}"
        
        db_obj = Quote(
            quote_number=quote_number,
            client_id=obj_in.client_id,
            lead_id=obj_in.lead_id,
            issue_date=obj_in.issue_date,
            expiry_date=obj_in.expiry_date,
            status=obj_in.status,
            currency=obj_in.currency,
            subtotal=obj_in.subtotal,
            tax_amount=obj_in.tax_amount,
            total_amount=obj_in.total_amount,
            notes=obj_in.notes,
            file_url=obj_in.file_url
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        for item in obj_in.items:
            db_item = QuoteItem(
                quote_id=db_obj.id,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            )
            db.add(db_item)
        
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Quote, obj_in: QuoteUpdate):
        update_data = obj_in.dict(exclude_unset=True)
        items_data = update_data.pop("items", None)

        for field in update_data:
            setattr(db_obj, field, update_data[field])

        if items_data is not None:
            # Simple approach: delete existing and replace to maintain sync nicely
            db.query(QuoteItem).filter(QuoteItem.quote_id == db_obj.id).delete()
            for item in items_data:
                db_item = QuoteItem(
                    quote_id=db_obj.id,
                    product_id=item.get("product_id"),
                    description=item.get("description"),
                    quantity=item.get("quantity"),
                    unit_price=item.get("unit_price"),
                    total_price=item.get("total_price")
                )
                db.add(db_item)

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int):
        obj = db.query(Quote).get(id)
        db.delete(obj)
        db.commit()
        return obj

quote_repository = QuoteRepository()
