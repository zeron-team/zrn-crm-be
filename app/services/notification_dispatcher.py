"""
Notification Dispatcher — central orchestrator.
Given an event_type and user_id, looks up preferences and dispatches
to the appropriate channel senders.
"""
import logging
from sqlalchemy.orm import Session

from app.models.notification_preference import NotificationPreference
from app.models.notification_log import NotificationLog
from app.models.user import User
from app.models.email_account import EmailAccount
from app.services.email_sender import send_email_notification
from app.services.telegram_sender import send_telegram_notification
from app.services.discord_sender import send_discord_notification
from app.services.whatsapp_sender import send_whatsapp_notification

logger = logging.getLogger(__name__)

# Human-readable labels for event types (used in notification titles)
EVENT_LABELS = {
    "calendar_reminder": "Recordatorio de Cita",
    "quote_expiration": "Vencimiento de Cuota",
    "sprint_ending": "Sprint por Vencer",
    "invoice_emitted": "Factura Emitida",
    "task_assigned": "Tarea Asignada",
    "stock_low": "Stock Bajo",
    "ticket_update": "Actualización de Ticket",
}


def dispatch_notification(
    db: Session,
    user_id: int,
    event_type: str,
    title: str,
    body: str,
):
    """
    Main entry point: dispatch a notification to all enabled channels
    for the given user and event type.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.warning(f"Notification dispatch: user {user_id} not found")
        return

    # Get enabled preferences for this user + event
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id,
        NotificationPreference.event_type == event_type,
        NotificationPreference.enabled == True,
    ).all()

    if not prefs:
        logger.debug(f"No enabled notification preferences for user {user_id}, event {event_type}")
        return

    for pref in prefs:
        result = _send_to_channel(db, user, pref.channel, title, body)

        # Log the result
        log_entry = NotificationLog(
            user_id=user_id,
            event_type=event_type,
            channel=pref.channel,
            title=title,
            body=body,
            status="sent" if result["success"] else "failed",
            error_message=result.get("error"),
        )
        db.add(log_entry)

    db.commit()


def send_test_notification(db: Session, user: User, channel: str, message: str = None) -> dict:
    """Send a test notification to a single channel for the given user."""
    title = "🔔 Notificación de Prueba"
    body = message or "Esta es una notificación de prueba desde Zeron CRM 360°. ¡Todo funciona correctamente!"

    result = _send_to_channel(db, user, channel, title, body)

    # Log it
    log_entry = NotificationLog(
        user_id=user.id,
        event_type="test",
        channel=channel,
        title=title,
        body=body,
        status="sent" if result["success"] else "failed",
        error_message=result.get("error"),
    )
    db.add(log_entry)
    db.commit()

    return result


def _send_to_channel(db: Session, user: User, channel: str, title: str, body: str) -> dict:
    """Route a notification to the appropriate sender."""
    if channel == "email":
        return _send_email(db, user, title, body)
    elif channel == "telegram":
        return send_telegram_notification(user.telegram_chat_id, title, body)
    elif channel == "discord":
        return send_discord_notification(user.discord_webhook_url, title, body)
    elif channel == "whatsapp":
        return send_whatsapp_notification(user.mobile, title, body)
    else:
        return {"success": False, "error": f"Unknown channel: {channel}"}


def _send_email(db: Session, user: User, title: str, body: str) -> dict:
    """Send email using the user's default SMTP account."""
    account = db.query(EmailAccount).filter(
        EmailAccount.user_id == user.id,
        EmailAccount.is_default == True,
    ).first()

    if not account:
        # Fall back to any account
        account = db.query(EmailAccount).filter(
            EmailAccount.user_id == user.id,
        ).first()

    if not account:
        return {"success": False, "error": "No email account configured for this user"}

    return send_email_notification(
        smtp_host=account.smtp_host,
        smtp_port=account.smtp_port,
        smtp_user=account.smtp_user,
        smtp_password=account.smtp_password,
        smtp_ssl=account.smtp_ssl,
        from_addr=account.email_address,
        to_addr=user.email,
        subject=f"Zeron CRM — {title}",
        body=body,
    )


def get_channel_status(db: Session, user: User) -> list:
    """Check which channels the user has configured."""
    channels = []

    # Email
    email_account = db.query(EmailAccount).filter(
        EmailAccount.user_id == user.id,
    ).first()
    channels.append({
        "channel": "email",
        "configured": email_account is not None,
        "detail": email_account.email_address if email_account else "Sin cuenta SMTP configurada",
    })

    # Telegram
    channels.append({
        "channel": "telegram",
        "configured": bool(user.telegram_chat_id),
        "detail": f"Chat ID: {user.telegram_chat_id}" if user.telegram_chat_id else "Sin chat_id configurado",
    })

    # WhatsApp
    channels.append({
        "channel": "whatsapp",
        "configured": bool(user.mobile),
        "detail": user.mobile if user.mobile else "Sin número móvil configurado",
    })

    # Discord
    channels.append({
        "channel": "discord",
        "configured": bool(user.discord_webhook_url),
        "detail": "Webhook configurado" if user.discord_webhook_url else "Sin webhook configurado",
    })

    return channels
