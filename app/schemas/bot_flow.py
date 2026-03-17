from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class BotFlowBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: Optional[bool] = False
    trigger_type: Optional[str] = "keyword"
    trigger_value: Optional[str] = None
    nodes: Optional[List[Any]] = []
    edges: Optional[List[Any]] = []


class BotFlowCreate(BotFlowBase):
    pass


class BotFlowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    trigger_type: Optional[str] = None
    trigger_value: Optional[str] = None
    nodes: Optional[List[Any]] = None
    edges: Optional[List[Any]] = None


class BotFlowResponse(BotFlowBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
