from sqlalchemy import Column, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class DashboardConfig(Base):
    __tablename__ = "dashboard_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    widgets = Column(JSON, nullable=False, default=list)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
