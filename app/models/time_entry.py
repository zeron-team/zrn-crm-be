from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)

    # check_in, check_out, break_start, break_end, meal_start, meal_end
    entry_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, server_default=func.now())
    notes = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    employee = relationship("Employee", back_populates="time_entries")
