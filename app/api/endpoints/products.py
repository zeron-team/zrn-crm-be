from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services.product import product_service

router = APIRouter()

@router.post("/", response_model=ProductResponse)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    return product_service.create_product(db, product_in=product_in)

@router.get("/", response_model=List[ProductResponse])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return product_service.get_products(db, skip=skip, limit=limit)

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    return product_service.get_product(db, product_id=product_id)

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, product_in: ProductUpdate, db: Session = Depends(get_db)):
    return product_service.update_product(db, product_id=product_id, product_in=product_in)

@router.delete("/{product_id}", response_model=ProductResponse)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    return product_service.delete_product(db, product_id=product_id)
