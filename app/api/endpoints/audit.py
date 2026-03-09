"""
Audit Log API Endpoints
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.audit_log import AuditLog
from app.api.endpoints.auth import get_current_user

router = APIRouter()


@router.get("/")
def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    severity: Optional[str] = None,
    days: int = Query(default=7, le=90),
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Query audit logs. Only admins can access."""
    if "admin" not in (current_user.role or ""):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver logs de auditoría")

    query = db.query(AuditLog)
    since = datetime.utcnow() - timedelta(days=days)
    query = query.filter(AuditLog.timestamp >= since)

    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if severity:
        query = query.filter(AuditLog.severity == severity)

    logs = query.order_by(desc(AuditLog.timestamp)).limit(limit).all()

    return {
        "total": len(logs),
        "logs": [
            {
                "id": log.id,
                "timestamp": str(log.timestamp),
                "user_id": log.user_id,
                "user_email": log.user_email,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "entity_name": log.entity_name,
                "ip_address": log.ip_address,
                "details": log.details,
                "severity": log.severity,
            }
            for log in logs
        ],
    }


@router.get("/summary")
def get_audit_summary(
    days: int = Query(default=7, le=90),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get audit log summary (counts by action type)."""
    if "admin" not in (current_user.role or ""):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Solo administradores")

    from sqlalchemy import func
    since = datetime.utcnow() - timedelta(days=days)

    results = (
        db.query(AuditLog.action, func.count(AuditLog.id))
        .filter(AuditLog.timestamp >= since)
        .group_by(AuditLog.action)
        .all()
    )

    return {
        "period_days": days,
        "actions": {action: count for action, count in results},
        "total": sum(count for _, count in results),
    }
