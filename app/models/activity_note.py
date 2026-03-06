from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class ActivityNote(Base):
    __tablename__ = "activity_notes"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("calendar_events.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    event = relationship("CalendarEvent", back_populates="notes")
