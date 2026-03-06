from sqlalchemy.orm import Session
from app.repositories.product import product_repository
from app.schemas.product import ProductCreate, ProductUpdate
from fastapi import HTTPException, status

class ProductService:
    def create_product(self, db: Session, product_in: ProductCreate):
        return product_repository.create(db, obj_in=product_in)

    def get_product(self, db: Session, product_id: int):
        product = product_repository.get(db, id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
        
    def get_products(self, db: Session, skip: int = 0, limit: int = 100):
        return product_repository.get_multi(db, skip=skip, limit=limit)

    def update_product(self, db: Session, product_id: int, product_in: ProductUpdate):
        product = product_repository.get(db, id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product_repository.update(db, db_obj=product, obj_in=product_in)

    def delete_product(self, db: Session, product_id: int):
        product = product_repository.get(db, id=product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product_repository.remove(db, id=product_id)

product_service = ProductService()
