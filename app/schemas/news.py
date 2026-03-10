from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NewsBase(BaseModel):
    title: str
    content: str
    category: str = "General"
    image_url: Optional[str] = None
    is_pinned: bool = False
    status: str = "draft"       # draft, published, archived
    priority: str = "normal"    # normal, important, urgent


class NewsCreate(NewsBase):
    pass


class NewsUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    is_pinned: Optional[bool] = None
    status: Optional[str] = None
    priority: Optional[str] = None


class NewsAuthor(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str
    avatar_url: Optional[str] = None

    class Config:
        from_attributes = True


class NewsResponse(NewsBase):
    id: int
    author_id: int
    author: Optional[NewsAuthor] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
