"""
User Profile self-service endpoints.
Separate router at /profile to avoid /{user_id} conflicts.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import os, uuid

from app.database import get_db
from app.schemas.user import UserResponse, ProfileUpdate
from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "uploads")
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")


@router.get("/", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's full profile."""
    return current_user


@router.put("/", response_model=UserResponse)
def update_my_profile(
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the current user's personal profile data."""
    update_data = profile_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload or replace the current user's avatar image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Solo se permiten imágenes")

    os.makedirs(AVATAR_DIR, exist_ok=True)

    if current_user.avatar_url:
        old_name = current_user.avatar_url.split("/")[-1]
        old_path = os.path.join(AVATAR_DIR, old_name)
        if os.path.exists(old_path):
            os.remove(old_path)

    ext = file.filename.split(".")[-1] if "." in file.filename else "png"
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(AVATAR_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    current_user.avatar_url = f"/uploads/avatars/{filename}"
    db.commit()
    db.refresh(current_user)
    return {"avatar_url": current_user.avatar_url}


@router.delete("/avatar")
def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete the current user's avatar."""
    if current_user.avatar_url:
        old_name = current_user.avatar_url.split("/")[-1]
        old_path = os.path.join(AVATAR_DIR, old_name)
        if os.path.exists(old_path):
            os.remove(old_path)
        current_user.avatar_url = None
        db.commit()
    return {"ok": True}
