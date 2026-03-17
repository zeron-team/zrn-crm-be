"""
Notification Preferences API — CRUD for user notification preferences.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.notification_preference import NotificationPreference
from app.models.notification_log import NotificationLog
from app.api.endpoints.auth import get_current_user
from app.schemas.notification_schemas import (
    NotificationPreferenceBatch,
    NotificationPreferenceResponse,
    NotificationTestRequest,
    NotificationTestResponse,
    NotificationLogResponse,
    ChannelStatus,
    ChannelsStatusResponse,
    EventTypeInfo,
    NotificationMetaResponse,
    EVENT_TYPES,
    CHANNELS,
)
from app.services.notification_dispatcher import (
    send_test_notification,
    get_channel_status,
)

router = APIRouter(prefix="/notification-preferences", tags=["notification-preferences"])


# ── Metadata for frontend ──
EVENT_TYPE_META = {
    "calendar_reminder": {"label": "Citas / Reuniones", "description": "Recordatorios de eventos del calendario, llamadas y reuniones"},
    "quote_expiration": {"label": "Vencimientos de Cuotas", "description": "Cuotas de presupuestos próximas a vencer"},
    "sprint_ending": {"label": "Sprints por Vencer", "description": "Sprints activos que están por finalizar"},
    "invoice_emitted": {"label": "Facturas Emitidas", "description": "Cuando se emite una nueva factura"},
    "task_assigned": {"label": "Tareas Asignadas", "description": "Cuando te asignan una nueva tarea"},
    "stock_low": {"label": "Stock Bajo", "description": "Alertas de producto con stock por debajo del mínimo"},
    "ticket_update": {"label": "Tickets de Soporte", "description": "Actualizaciones en tickets de soporte asignados"},
}


@router.get("/meta", response_model=NotificationMetaResponse)
def get_notification_meta():
    """Return available event types and channels for the preference matrix."""
    event_types = [
        EventTypeInfo(key=k, label=v["label"], description=v["description"])
        for k, v in EVENT_TYPE_META.items()
    ]
    return NotificationMetaResponse(event_types=event_types, channels=CHANNELS)


@router.get("/", response_model=list[NotificationPreferenceResponse])
def list_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all notification preferences for the current user."""
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id,
    ).all()
    return prefs


@router.put("/", response_model=list[NotificationPreferenceResponse])
def upsert_preferences(
    batch: NotificationPreferenceBatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or update notification preferences in batch (full matrix save)."""
    results = []

    for item in batch.preferences:
        if item.channel not in CHANNELS:
            raise HTTPException(status_code=400, detail=f"Invalid channel: {item.channel}")
        if item.event_type not in EVENT_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid event_type: {item.event_type}")

        # Upsert
        existing = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == current_user.id,
            NotificationPreference.event_type == item.event_type,
            NotificationPreference.channel == item.channel,
        ).first()

        if existing:
            existing.enabled = item.enabled
            results.append(existing)
        else:
            new_pref = NotificationPreference(
                user_id=current_user.id,
                event_type=item.event_type,
                channel=item.channel,
                enabled=item.enabled,
            )
            db.add(new_pref)
            db.flush()
            results.append(new_pref)

    db.commit()
    for r in results:
        db.refresh(r)
    return results


@router.get("/channels", response_model=ChannelsStatusResponse)
def get_channels_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check which notification channels are configured for the current user."""
    statuses = get_channel_status(db, current_user)
    return ChannelsStatusResponse(channels=[ChannelStatus(**s) for s in statuses])


@router.post("/test/{channel}", response_model=NotificationTestResponse)
def test_channel(
    channel: str,
    body: Optional[NotificationTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a test notification to a specific channel."""
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail=f"Invalid channel: {channel}")

    message = body.message if body else None
    result = send_test_notification(db, current_user, channel, message)

    return NotificationTestResponse(
        success=result["success"],
        message="Notificación enviada correctamente" if result["success"] else f"Error: {result.get('error', 'Unknown')}",
    )


# ── Notification Logs ──
logs_router = APIRouter(prefix="/notification-logs", tags=["notification-logs"])


@logs_router.get("/", response_model=list[NotificationLogResponse])
def list_logs(
    limit: int = Query(50, ge=1, le=200),
    channel: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notification logs for the current user."""
    query = db.query(NotificationLog).filter(
        NotificationLog.user_id == current_user.id,
    )
    if channel:
        query = query.filter(NotificationLog.channel == channel)

    logs = query.order_by(NotificationLog.sent_at.desc()).limit(limit).all()
    return logs
