from pydantic import BaseModel
from typing import Optional, List

# --- Family (top level) ---
class FamilyBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None

class FamilyCreate(FamilyBase):
    pass

class FamilyUpdate(FamilyBase):
    name: Optional[str] = None

class FamilyResponse(FamilyBase):
    id: int
    class Config:
        from_attributes = True

# --- Category (belongs to Family) ---
class CategoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    family_id: int

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    family_id: Optional[int] = None

class CategoryResponse(CategoryBase):
    id: int
    class Config:
        from_attributes = True

# --- Subcategory (belongs to Category) ---
class SubcategoryBase(BaseModel):
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    category_id: int

class SubcategoryCreate(SubcategoryBase):
    pass

class SubcategoryUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

class SubcategoryResponse(SubcategoryBase):
    id: int
    class Config:
        from_attributes = True

# --- Tree response (Family → Category → Subcategory) ---
class SubcategoryTreeItem(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    class Config:
        from_attributes = True

class CategoryTreeItem(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    subcategories: List[SubcategoryTreeItem] = []
    class Config:
        from_attributes = True

class FamilyTreeItem(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    description: Optional[str] = None
    categories: List[CategoryTreeItem] = []
    class Config:
        from_attributes = True
