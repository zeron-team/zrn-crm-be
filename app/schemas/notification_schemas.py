"""Pydantic schemas for the Notification system."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ── Event types ──
EVENT_TYPES = [
    "calendar_reminder",
    "quote_expiration",
    "sprint_ending",
    "invoice_emitted",
    "task_assigned",
    "stock_low",
    "ticket_update",
]

CHANNELS = ["email", "telegram", "whatsapp", "discord"]


# ── Preference schemas ──
class NotificationPreferenceItem(BaseModel):
    event_type: str
    channel: str
    enabled: bool = True


class NotificationPreferenceBatch(BaseModel):
    """Batch update: a full list of preferences to upsert."""
    preferences: List[NotificationPreferenceItem]


class NotificationPreferenceResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    channel: str
    enabled: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Channel status ──
class ChannelStatus(BaseModel):
    channel: str
    configured: bool
    detail: Optional[str] = None  # e.g. "Telegram chat_id: 12345"


class ChannelsStatusResponse(BaseModel):
    channels: List[ChannelStatus]


# ── Test notification ──
class NotificationTestRequest(BaseModel):
    channel: str
    message: Optional[str] = "🔔 Notificación de prueba desde Zeron CRM"


class NotificationTestResponse(BaseModel):
    success: bool
    message: str


# ── Log schemas ──
class NotificationLogResponse(BaseModel):
    id: int
    user_id: int
    event_type: str
    channel: str
    title: str
    body: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Metadata for the frontend ──
class EventTypeInfo(BaseModel):
    key: str
    label: str
    description: str


class NotificationMetaResponse(BaseModel):
    event_types: List[EventTypeInfo]
    channels: List[str]
