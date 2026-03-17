from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, Boolean, Table
from sqlalchemy.orm import relationship
from app.database import Base

# Many-to-many junction table for calendar events <-> contacts
calendar_event_contacts = Table(
    "calendar_event_contacts",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), primary_key=True),
    Column("contact_id", Integer, ForeignKey("contacts.id", ondelete="CASCADE"), primary_key=True),
)

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
    contact_id = Column(Integer, ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True)  # legacy single contact
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)

    # Status tracking
    status = Column(String, default="pending")  # pending, completed, postponed, cancelled
    status_reason = Column(Text, nullable=True)

    # Follow-up chain
    parent_event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)

    # Call fields
    call_url = Column(String(500), nullable=True)        # Zoom/Meet/Teams link
    is_recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String(50), nullable=True)  # daily, weekly, biweekly, monthly
    recurrence_end_date = Column(Date, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    contacts = relationship("Contact", secondary=calendar_event_contacts, backref="calendar_events", lazy="joined")
    notes = relationship("ActivityNote", back_populates="event", cascade="all, delete-orphan", order_by="ActivityNote.created_at.desc()")
    follow_ups = relationship("CalendarEvent", backref="parent_event", remote_side=[id])
    project = relationship("Project", backref="calendar_events_rel")
