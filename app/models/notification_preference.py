"""Notification Preferences — per-user, per-event, per-channel settings."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint("user_id", "event_type", "channel", name="uq_user_event_channel"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    # event_type values:
    #   calendar_reminder, quote_expiration, sprint_ending,
    #   invoice_emitted, task_assigned, stock_low, ticket_update, custom
    channel = Column(String(20), nullable=False)
    # channel values: email, telegram, whatsapp, discord
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
