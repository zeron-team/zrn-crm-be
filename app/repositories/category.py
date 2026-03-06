from sqlalchemy.orm import Session, joinedload
from app.models.category import Family, Category, Subcategory
from app.schemas.category import (
    FamilyCreate, FamilyUpdate,
    CategoryCreate, CategoryUpdate,
    SubcategoryCreate, SubcategoryUpdate,
)


class CategoryRepository:
    # --- Family (top level) ---
    def get_family(self, db: Session, id: int):
        return db.query(Family).filter(Family.id == id).first()

    def get_families(self, db: Session):
        return db.query(Family).order_by(Family.name).all()

    def create_family(self, db: Session, obj_in: FamilyCreate):
        db_obj = Family(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_family(self, db: Session, db_obj: Family, obj_in: FamilyUpdate):
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_family(self, db: Session, id: int):
        obj = db.query(Family).get(id)
        db.delete(obj)
        db.commit()
        return obj

    # --- Category (belongs to Family) ---
    def get_category(self, db: Session, id: int):
        return db.query(Category).filter(Category.id == id).first()

    def get_categories(self, db: Session, family_id: int | None = None):
        q = db.query(Category)
        if family_id:
            q = q.filter(Category.family_id == family_id)
        return q.order_by(Category.name).all()

    def create_category(self, db: Session, obj_in: CategoryCreate):
        db_obj = Category(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_category(self, db: Session, db_obj: Category, obj_in: CategoryUpdate):
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_category(self, db: Session, id: int):
        obj = db.query(Category).get(id)
        db.delete(obj)
        db.commit()
        return obj

    # --- Subcategory (belongs to Category) ---
    def get_subcategory(self, db: Session, id: int):
        return db.query(Subcategory).filter(Subcategory.id == id).first()

    def get_subcategories(self, db: Session, category_id: int | None = None):
        q = db.query(Subcategory)
        if category_id:
            q = q.filter(Subcategory.category_id == category_id)
        return q.order_by(Subcategory.name).all()

    def create_subcategory(self, db: Session, obj_in: SubcategoryCreate):
        db_obj = Subcategory(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_subcategory(self, db: Session, db_obj: Subcategory, obj_in: SubcategoryUpdate):
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete_subcategory(self, db: Session, id: int):
        obj = db.query(Subcategory).get(id)
        db.delete(obj)
        db.commit()
        return obj

    # --- Tree: Family → Category → Subcategory ---
    def get_tree(self, db: Session):
        return (
            db.query(Family)
            .options(
                joinedload(Family.categories).joinedload(Category.subcategories)
            )
            .order_by(Family.name)
            .all()
        )


category_repository = CategoryRepository()
