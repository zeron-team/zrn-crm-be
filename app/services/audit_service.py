"""
Audit Logging Service for ZeRoN 360°
Records critical actions for security compliance and traceability.
"""

import logging
from typing import Optional, Any
from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict] = None,
    severity: str = "info",
):
    """Record an audit log entry."""
    try:
        entry = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            user_id=user_id,
            user_email=user_email,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details,
            severity=severity,
        )
        db.add(entry)
        db.commit()
    except Exception as e:
        logger.error(f"Audit log error: {e}")
        db.rollback()


def log_from_request(
    db: Session,
    request: Request,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    entity_name: Optional[str] = None,
    user: Any = None,
    details: Optional[dict] = None,
    severity: str = "info",
):
    """Record an audit log entry from a FastAPI request (auto-extracts IP/UA)."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")[:500]
    uid = getattr(user, "id", None) if user else None
    uemail = getattr(user, "email", None) if user else None

    log_action(
        db=db,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_name=entity_name,
        user_id=uid,
        user_email=uemail,
        ip_address=ip,
        user_agent=ua,
        details=details,
        severity=severity,
    )
