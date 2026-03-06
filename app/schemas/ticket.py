from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Ticket Comment ---

class TicketCommentBase(BaseModel):
    content: str
    is_internal: Optional[bool] = False
    comment_type: Optional[str] = "comment"

class TicketCommentCreate(TicketCommentBase):
    user_id: Optional[int] = None

class TicketCommentResponse(TicketCommentBase):
    id: int
    ticket_id: int
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Ticket ---

class TicketBase(BaseModel):
    subject: str
    description: Optional[str] = None
    status: Optional[str] = "open"
    priority: Optional[str] = "medium"
    category: Optional[str] = "general"
    client_id: Optional[int] = None
    assigned_to: Optional[int] = None

class TicketCreate(TicketBase):
    created_by: Optional[int] = None

class TicketUpdate(BaseModel):
    subject: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None
    client_id: Optional[int] = None
    assigned_to: Optional[int] = None

class TicketResponse(TicketBase):
    id: int
    ticket_number: str
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    client_name: Optional[str] = None
    assignee_name: Optional[str] = None
    creator_name: Optional[str] = None
    comment_count: Optional[int] = 0

    class Config:
        from_attributes = True

class TicketDetailResponse(TicketResponse):
    comments: List[TicketCommentResponse] = []
