from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database import get_db
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.user import user_service
from app.api.endpoints.auth import get_current_user
from app.models.user import User

router = APIRouter()

# ═══ In-memory online tracking ═══
# Dict of user_id -> { last_seen, email, full_name }
_online_users: dict = {}
ONLINE_THRESHOLD_SECONDS = 120  # 2 minutes


@router.post("/", response_model=UserResponse)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    return user_service.create_user(db, user_in=user_in)

@router.get("/", response_model=List[UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return user_service.get_users(db, skip=skip, limit=limit)

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
    # Clean up expired entries
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
    # Update last_login in DB on first heartbeat or every 60s
    should_update = not prev or (now - prev["last_seen"]).total_seconds() >= 60
    if should_update:
        current_user.last_login = now
        db.commit()
    return {"ok": True}

@router.get("/{user_id}", response_model=UserResponse)
def read_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.get_user(db, user_id=user_id)

@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db)):
    return user_service.update_user(db, user_id=user_id, user_in=user_in)

@router.delete("/{user_id}", response_model=UserResponse)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return user_service.delete_user(db, user_id=user_id)

