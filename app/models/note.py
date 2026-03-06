from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="")
    content = Column(Text, nullable=True)
    color = Column(String(20), default="yellow")  # yellow, green, blue, pink, purple, orange
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)

    # Polymorphic entity association
    entity_type = Column(String(50), nullable=True, index=True)  # client, lead, provider, contact, invoice, quote, ticket
    entity_id = Column(Integer, nullable=True, index=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("User", foreign_keys=[created_by], backref="created_notes")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_notes")
