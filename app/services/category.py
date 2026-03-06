from sqlalchemy.orm import Session
from app.repositories.category import category_repository
from app.schemas.category import (
    FamilyCreate, FamilyUpdate,
    CategoryCreate, CategoryUpdate,
    SubcategoryCreate, SubcategoryUpdate,
)
from fastapi import HTTPException


class CategoryService:
    # --- Family (top level) ---
    def create_family(self, db: Session, obj_in: FamilyCreate):
        return category_repository.create_family(db, obj_in)

    def get_families(self, db: Session):
        return category_repository.get_families(db)

    def get_family(self, db: Session, id: int):
        fam = category_repository.get_family(db, id)
        if not fam:
            raise HTTPException(status_code=404, detail="Family not found")
        return fam

    def update_family(self, db: Session, id: int, obj_in: FamilyUpdate):
        fam = self.get_family(db, id)
        return category_repository.update_family(db, fam, obj_in)

    def delete_family(self, db: Session, id: int):
        self.get_family(db, id)
        return category_repository.delete_family(db, id)

    # --- Category (belongs to Family) ---
    def create_category(self, db: Session, obj_in: CategoryCreate):
        self.get_family(db, obj_in.family_id)
        return category_repository.create_category(db, obj_in)

    def get_categories(self, db: Session, family_id: int | None = None):
        return category_repository.get_categories(db, family_id)

    def get_category(self, db: Session, id: int):
        cat = category_repository.get_category(db, id)
        if not cat:
            raise HTTPException(status_code=404, detail="Category not found")
        return cat

    def update_category(self, db: Session, id: int, obj_in: CategoryUpdate):
        cat = self.get_category(db, id)
        return category_repository.update_category(db, cat, obj_in)

    def delete_category(self, db: Session, id: int):
        self.get_category(db, id)
        return category_repository.delete_category(db, id)

    # --- Subcategory (belongs to Category) ---
    def create_subcategory(self, db: Session, obj_in: SubcategoryCreate):
        self.get_category(db, obj_in.category_id)
        return category_repository.create_subcategory(db, obj_in)

    def get_subcategories(self, db: Session, category_id: int | None = None):
        return category_repository.get_subcategories(db, category_id)

    def get_subcategory(self, db: Session, id: int):
        sub = category_repository.get_subcategory(db, id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subcategory not found")
        return sub

    def update_subcategory(self, db: Session, id: int, obj_in: SubcategoryUpdate):
        sub = self.get_subcategory(db, id)
        return category_repository.update_subcategory(db, sub, obj_in)

    def delete_subcategory(self, db: Session, id: int):
        self.get_subcategory(db, id)
        return category_repository.delete_subcategory(db, id)

    # --- Tree ---
    def get_tree(self, db: Session):
        return category_repository.get_tree(db)


category_service = CategoryService()
