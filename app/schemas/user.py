from pydantic import BaseModel, EmailStr
from typing import Optional

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

    class Config:
        from_attributes = True

class UserResponse(UserInDBBase):
    pass
