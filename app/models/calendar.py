from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    related_to = Column(String) # E.g., "Meeting", "Billing", "Service Expiration", "Other"
    color = Column(String, default="#3788d8")
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)

    # Status tracking
    status = Column(String, default="pending")  # pending, completed, postponed, cancelled
    status_reason = Column(Text, nullable=True)

    # Follow-up chain
    parent_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    notes = relationship("ActivityNote", back_populates="event", cascade="all, delete-orphan", order_by="ActivityNote.created_at.desc()")
    follow_ups = relationship("CalendarEvent", backref="parent_event", remote_side=[id])
