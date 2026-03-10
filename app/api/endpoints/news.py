"""
Company News / Announcements endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import os, uuid

from app.database import get_db
from app.models.news import News, NewsDismissal
from app.models.user import User
from app.schemas.news import NewsCreate, NewsUpdate, NewsResponse
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/news", tags=["news"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "uploads")
NEWS_IMG_DIR = os.path.join(UPLOAD_DIR, "news")

# Current app version for welcome modal dismissal
CURRENT_VERSION = "6.1.0"


@router.get("/", response_model=List[NewsResponse])
def list_news(
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List news articles. Pinned first, then by date descending."""
    q = db.query(News)
    if category:
        q = q.filter(News.category == category)
    q = q.order_by(desc(News.is_pinned), desc(News.created_at))
    return q.offset(skip).limit(limit).all()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    """Return distinct categories used in news."""
    rows = db.query(News.category).distinct().all()
    return [r[0] for r in rows if r[0]]


@router.post("/", response_model=NewsResponse)
def create_news(
    news_in: NewsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a news article (admin/superadmin only)."""
    role = current_user.role or ""
    if "admin" not in role and "superadmin" not in role:
        raise HTTPException(status_code=403, detail="Solo administradores pueden publicar noticias")
    news = News(**news_in.model_dump(), author_id=current_user.id)
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


@router.put("/{news_id}", response_model=NewsResponse)
def update_news(
    news_id: int,
    news_in: NewsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a news article."""
    role = current_user.role or ""
    if "admin" not in role and "superadmin" not in role:
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar noticias")
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    for field, value in news_in.model_dump(exclude_unset=True).items():
        setattr(news, field, value)
    db.commit()
    db.refresh(news)
    return news


@router.delete("/{news_id}")
def delete_news(
    news_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a news article."""
    role = current_user.role or ""
    if "admin" not in role and "superadmin" not in role:
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar noticias")
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    # Delete image if exists
    if news.image_url:
        img_name = news.image_url.split("/")[-1]
        img_path = os.path.join(NEWS_IMG_DIR, img_name)
        if os.path.exists(img_path):
            os.remove(img_path)
    db.delete(news)
    db.commit()
    return {"ok": True}


@router.post("/{news_id}/image")
async def upload_news_image(
    news_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an image for a news article."""
    role = current_user.role or ""
    if "admin" not in role and "superadmin" not in role:
        raise HTTPException(status_code=403, detail="Solo administradores")
    news = db.query(News).filter(News.id == news_id).first()
    if not news:
        raise HTTPException(status_code=404, detail="Noticia no encontrada")
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes")

    os.makedirs(NEWS_IMG_DIR, exist_ok=True)

    # Delete old image
    if news.image_url:
        old_name = news.image_url.split("/")[-1]
        old_path = os.path.join(NEWS_IMG_DIR, old_name)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"news_{news_id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(NEWS_IMG_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    news.image_url = f"/uploads/news/{filename}"
    db.commit()
    db.refresh(news)
    return {"image_url": news.image_url}


# ─── Welcome modal dismiss ─────────────────────────────────

@router.get("/welcome-status")
def welcome_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Check if the welcome modal should be shown for this user."""
    dismissal = db.query(NewsDismissal).filter(
        NewsDismissal.user_id == current_user.id
    ).first()
    show = not dismissal or dismissal.dismissed_version != CURRENT_VERSION
    return {"show_welcome": show, "current_version": CURRENT_VERSION}


@router.post("/dismiss-welcome")
def dismiss_welcome(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Dismiss the welcome modal for this user."""
    dismissal = db.query(NewsDismissal).filter(
        NewsDismissal.user_id == current_user.id
    ).first()
    if dismissal:
        dismissal.dismissed_version = CURRENT_VERSION
    else:
        dismissal = NewsDismissal(user_id=current_user.id, dismissed_version=CURRENT_VERSION)
        db.add(dismissal)
    db.commit()
    return {"ok": True}
