from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    role: Optional[str] = "user"
    commission_pct: Optional[float] = 0

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class UserInDBBase(UserBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    dni: Optional[str] = None
    cuil: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    blood_type: Optional[str] = None
    bio: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None

    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    pass


class ProfileUpdate(BaseModel):
    """Schema for self-service profile updates — users can only edit these fields."""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    dni: Optional[str] = None
    cuil: Optional[str] = None
    birth_date: Optional[date] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    marital_status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    blood_type: Optional[str] = None
    bio: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
