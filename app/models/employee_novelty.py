from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class EmployeeNovelty(Base):
    """Employee novelties: leaves, absences, vacations, overtime, medical, etc."""
    __tablename__ = "employee_novelties"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    # Type: vacation, medical_leave, personal_leave, absence, overtime, late_arrival,
    #        maternity, paternity, study_leave, bereavement, compensatory, other
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending, approved, rejected, cancelled
    
    # Dates
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_count = Column(Float, default=1)  # Can be 0.5 for half day

    # Details
    reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)           # admin notes
    attachment_url = Column(String(500), nullable=True)  # medical certificate, etc.
    
    # Tracking
    requested_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    employee = relationship("Employee", backref="novelties")
    requester = relationship("User", foreign_keys=[requested_by], backref="requested_novelties")
    approver = relationship("User", foreign_keys=[approved_by], backref="approved_novelties")
