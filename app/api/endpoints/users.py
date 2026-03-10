from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import os, uuid

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse, ProfileUpdate
from app.services.user import user_service
from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

# ═══ In-memory online tracking ═══
_online_users: dict = {}
ONLINE_THRESHOLD_SECONDS = 120  # 2 minutes

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "uploads")
AVATAR_DIR = os.path.join(UPLOAD_DIR, "avatars")


@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if "superadmin" in (user_in.role or ""):
        if "superadmin" not in (current_user.role or ""):
            raise HTTPException(status_code=403, detail="Solo un Super Administrador puede asignar el rol superadmin")
    return user_service.create_user(db, user_in=user_in)

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.get_users(db, skip=skip, limit=limit)


# ═══════════════════════════════════════════════════════════
# /me/* ROUTES — must be BEFORE /{user_id} to avoid conflict
# ═══════════════════════════════════════════════════════════

@router.get("/online")
def get_online_users(current_user: User = Depends(get_current_user)):
    """Return list of users who pinged within the last ONLINE_THRESHOLD_SECONDS."""
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    online = []
    expired_keys = []
    for uid, info in _online_users.items():
        if info["last_seen"] >= cutoff:
            online.append({
                "id": uid,
                "email": info["email"],
                "full_name": info["full_name"],
                "last_seen": info["last_seen"].isoformat(),
            })
        else:
            expired_keys.append(uid)
    for k in expired_keys:
        _online_users.pop(k, None)
    return {"count": len(online), "users": online}

@router.post("/heartbeat")
def heartbeat(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Register a ping from the authenticated user."""
    now = datetime.utcnow()
    prev = _online_users.get(current_user.id)
    _online_users[current_user.id] = {
        "email": current_user.email,
        "full_name": current_user.full_name or current_user.email,
        "last_seen": now,
    }
    should_update = not prev or (now - prev["last_seen"]).total_seconds() >= 60
    if should_update:
        current_user.last_login = now
        db.commit()
    return {"ok": True}


@router.get("/me/profile", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the current user's full profile."""
    return current_user


@router.put("/me/profile", response_model=UserResponse)
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


@router.post("/me/avatar")
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


@router.delete("/me/avatar")
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


# ═══════════════════════════════════════════════════════════
# /{user_id} ROUTES — must be AFTER /me/* routes
# ═══════════════════════════════════════════════════════════

@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user(db, user_id=user_id)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if user_in.role and "superadmin" in user_in.role:
        if "superadmin" not in (current_user.role or ""):
            raise HTTPException(status_code=403, detail="Solo un Super Administrador puede asignar el rol superadmin")
    return user_service.update_user(db, user_id=user_id, user_in=user_in)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.delete_user(db, user_id=user_id)
