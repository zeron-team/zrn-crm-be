from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class ChatMessageOut(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionOut(BaseModel):
    session_id: str
    last_message: str
    message_count: int
    created_at: datetime
    updated_at: datetime
