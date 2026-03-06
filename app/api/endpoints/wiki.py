"""Wiki CRUD endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.wiki import WikiPage

router = APIRouter(prefix="/wiki", tags=["wiki"])


class WikiPageCreate(BaseModel):
    title: str
    content: Optional[str] = ""
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    parent_id: Optional[int] = None
    created_by: Optional[int] = None


class WikiPageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    parent_id: Optional[int] = None
    updated_by: Optional[int] = None


def page_to_dict(p: WikiPage):
    return {
        "id": p.id,
        "title": p.title,
        "content": p.content,
        "slug": p.slug,
        "entity_type": p.entity_type,
        "entity_id": p.entity_id,
        "parent_id": p.parent_id,
        "created_by": p.created_by,
        "updated_by": p.updated_by,
        "created_at": str(p.created_at) if p.created_at else None,
        "updated_at": str(p.updated_at) if p.updated_at else None,
    }


@router.get("/")
def list_pages(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(WikiPage)
    if entity_type:
        q = q.filter(WikiPage.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(WikiPage.entity_id == entity_id)
    if search:
        q = q.filter(WikiPage.title.ilike(f"%{search}%"))
    pages = q.order_by(WikiPage.updated_at.desc()).all()
    return [page_to_dict(p) for p in pages]


@router.get("/{page_id}")
def get_page(page_id: int, db: Session = Depends(get_db)):
    p = db.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not p:
        raise HTTPException(404, "Wiki page not found")
    d = page_to_dict(p)
    d["children"] = [page_to_dict(c) for c in db.query(WikiPage).filter(WikiPage.parent_id == page_id).all()]
    return d


@router.post("/")
def create_page(data: WikiPageCreate, db: Session = Depends(get_db)):
    slug = data.title.lower().replace(" ", "-").replace("/", "-")[:200]
    p = WikiPage(
        title=data.title,
        content=data.content or "",
        slug=slug,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        parent_id=data.parent_id,
        created_by=data.created_by,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return page_to_dict(p)


@router.put("/{page_id}")
def update_page(page_id: int, data: WikiPageUpdate, db: Session = Depends(get_db)):
    p = db.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not p:
        raise HTTPException(404, "Wiki page not found")
    for field in ["title", "content", "entity_type", "entity_id", "parent_id", "updated_by"]:
        val = getattr(data, field, None)
        if val is not None:
            setattr(p, field, val)
    if data.title:
        p.slug = data.title.lower().replace(" ", "-").replace("/", "-")[:200]
    p.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return page_to_dict(p)


@router.delete("/{page_id}")
def delete_page(page_id: int, db: Session = Depends(get_db)):
    p = db.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not p:
        raise HTTPException(404, "Wiki page not found")
    db.delete(p)
    db.commit()
    return {"ok": True}
