from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True, nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open", index=True)          # open, in_progress, waiting, resolved, closed
    priority = Column(String, default="medium", index=True)      # low, medium, high, critical
    category = Column(String, nullable=True)                     # general, billing, technical, other
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    # Relationships
    client = relationship("Client", backref="tickets")
    assignee = relationship("User", foreign_keys=[assigned_to], backref="assigned_tickets")
    creator = relationship("User", foreign_keys=[created_by], backref="created_tickets")
    comments = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketComment.created_at")


class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    content = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)                 # Internal note vs public comment
    comment_type = Column(String, default="comment")             # comment, status_change, assignment, note
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    ticket = relationship("Ticket", back_populates="comments")
    user = relationship("User", backref="ticket_comments")
