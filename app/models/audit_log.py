"""
Audit Log Model — Tracks all critical actions in the platform.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_email = Column(String(255), nullable=True)
    action = Column(String(50), nullable=False, index=True)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, EMIT_INVOICE
    entity_type = Column(String(50), nullable=True, index=True)  # client, invoice, ticket, user, arca_config, etc.
    entity_id = Column(Integer, nullable=True)
    entity_name = Column(String(255), nullable=True)  # human-readable identifier
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    details = Column(JSON, nullable=True)  # Extra context (changed fields, old values, etc.)
    severity = Column(String(10), default="info")  # info, warning, critical
