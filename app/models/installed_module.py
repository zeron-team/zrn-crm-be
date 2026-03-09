"""
InstalledModule — Tracks which modules are enabled/disabled and their licenses.
This is a NEW table that does NOT affect any existing tables.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class InstalledModule(Base):
    __tablename__ = "installed_modules"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    license_key = Column(Text, nullable=True)
    license_status = Column(String(20), default="trial")  # trial, active, expired
    license_expires_at = Column(DateTime, nullable=True)
    max_users = Column(Integer, default=0)  # 0 = unlimited
    installed_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Module metadata (denormalized for quick UI display)
    version = Column(String(20), default="1.0.0")
    description = Column(Text, nullable=True)
    icon = Column(String(50), nullable=True)
    category = Column(String(20), nullable=True)
    dependencies = Column(Text, default="[]")  # JSON array string
