from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.repositories.user import user_repository
from app.core.security import verify_password, create_access_token, decode_token, invalidate_token, maybe_upgrade_hash
from app.core.config import settings
from app.schemas.user import UserResponse
from app.services.audit_service import log_action
from datetime import timedelta, datetime

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Dependency to get the current authenticated user from JWT token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(token, settings.SECRET_KEY)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = user_repository.get(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/login", response_model=LoginResponse)
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = user_repository.get_by_email(db, login_data.email)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]
    if not user:
        log_action(db, action="LOGIN_FAILED", details={"email": login_data.email, "reason": "user_not_found"}, ip_address=ip, user_agent=ua, severity="warning")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(login_data.password, user.hashed_password):
        log_action(db, action="LOGIN_FAILED", user_id=user.id, user_email=user.email, details={"reason": "wrong_password"}, ip_address=ip, user_agent=ua, severity="warning")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role},
        secret_key=settings.SECRET_KEY,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    # Gradually upgrade bcrypt -> Argon2id on successful login
    def _update_hash(new_hash):
        user.hashed_password = new_hash
        db.commit()
    maybe_upgrade_hash(login_data.password, user.hashed_password, _update_hash)

    # Update last_login timestamp
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Audit log
    log_action(db, action="LOGIN", entity_type="user", entity_id=user.id, entity_name=user.email, user_id=user.id, user_email=user.email, ip_address=ip, user_agent=ua)

    return LoginResponse(access_token=access_token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    """Invalidate the current token (blacklist in Redis)."""
    if token:
        invalidate_token(token)
    return {"status": "ok", "message": "Logged out successfully"}
