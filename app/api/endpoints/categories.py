from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.category import (
    FamilyCreate, FamilyUpdate, FamilyResponse, FamilyTreeItem,
    CategoryCreate, CategoryUpdate, CategoryResponse,
    SubcategoryCreate, SubcategoryUpdate, SubcategoryResponse,
)
from app.services.category import category_service

router = APIRouter()

# ── Tree ────────────────────────────────────────────────

@router.get("/tree", response_model=List[FamilyTreeItem])
def get_category_tree(db: Session = Depends(get_db)):
    return category_service.get_tree(db)

# ── Families (top level) ────────────────────────────────

@router.get("/families", response_model=List[FamilyResponse])
def list_families(db: Session = Depends(get_db)):
    return category_service.get_families(db)

@router.post("/families", response_model=FamilyResponse)
def create_family(obj_in: FamilyCreate, db: Session = Depends(get_db)):
    return category_service.create_family(db, obj_in)

@router.put("/families/{family_id}", response_model=FamilyResponse)
def update_family(family_id: int, obj_in: FamilyUpdate, db: Session = Depends(get_db)):
    return category_service.update_family(db, family_id, obj_in)

@router.delete("/families/{family_id}", response_model=FamilyResponse)
def delete_family(family_id: int, db: Session = Depends(get_db)):
    return category_service.delete_family(db, family_id)

# ── Categories (belong to a Family) ────────────────────

@router.get("/", response_model=List[CategoryResponse])
def list_categories(family_id: Optional[int] = None, db: Session = Depends(get_db)):
    return category_service.get_categories(db, family_id)

@router.post("/", response_model=CategoryResponse)
def create_category(obj_in: CategoryCreate, db: Session = Depends(get_db)):
    return category_service.create_category(db, obj_in)

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, obj_in: CategoryUpdate, db: Session = Depends(get_db)):
    return category_service.update_category(db, category_id, obj_in)

@router.delete("/{category_id}", response_model=CategoryResponse)
def delete_category(category_id: int, db: Session = Depends(get_db)):
    return category_service.delete_category(db, category_id)

# ── Subcategories (belong to a Category) ────────────────

@router.get("/subcategories", response_model=List[SubcategoryResponse])
def list_subcategories(category_id: Optional[int] = None, db: Session = Depends(get_db)):
    return category_service.get_subcategories(db, category_id)

@router.post("/subcategories", response_model=SubcategoryResponse)
def create_subcategory(obj_in: SubcategoryCreate, db: Session = Depends(get_db)):
    return category_service.create_subcategory(db, obj_in)

@router.put("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
def update_subcategory(subcategory_id: int, obj_in: SubcategoryUpdate, db: Session = Depends(get_db)):
    return category_service.update_subcategory(db, subcategory_id, obj_in)

@router.delete("/subcategories/{subcategory_id}", response_model=SubcategoryResponse)
def delete_subcategory(subcategory_id: int, db: Session = Depends(get_db)):
    return category_service.delete_subcategory(db, subcategory_id)
