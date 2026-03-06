from sqlalchemy.orm import Session
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate

class ProductRepository:
    def get(self, db: Session, id: int) -> Product | None:
        return db.query(Product).filter(Product.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[Product]:
        return db.query(Product).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ProductCreate) -> Product:
        db_obj = Product(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: Product, obj_in: ProductUpdate) -> Product:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> Product:
        obj = db.query(Product).get(id)
        db.delete(obj)
        db.commit()
        return obj

product_repository = ProductRepository()
