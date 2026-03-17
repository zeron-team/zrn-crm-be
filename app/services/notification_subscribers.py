"""
Notification Event Bus Subscribers.
Subscribes to CRM events and triggers notification dispatch.
"""
import logging
from app.modules.events import event_bus, Events
from app.database import SessionLocal

logger = logging.getLogger(__name__)


def _dispatch_for_event(event_type: str, title: str, body: str, user_ids: list):
    """Helper to dispatch a notification for a list of user IDs."""
    from app.services.notification_dispatcher import dispatch_notification

    db = SessionLocal()
    try:
        for uid in user_ids:
            dispatch_notification(db, uid, event_type, title, body)
    except Exception as e:
        logger.error(f"❌ Notification subscriber error for {event_type}: {e}")
    finally:
        db.close()


def on_invoice_emitted(data):
    """When an invoice is emitted, notify relevant users."""
    if not data or not isinstance(data, dict):
        return
    user_ids = data.get("notify_user_ids", [])
    invoice_number = data.get("number", "N/A")
    client_name = data.get("client_name", "")
    _dispatch_for_event(
        "invoice_emitted",
        f"Factura {invoice_number} emitida",
        f"Se emitió la factura {invoice_number} para {client_name}.",
        user_ids,
    )


def on_stock_low(data):
    """When stock drops below threshold."""
    if not data or not isinstance(data, dict):
        return
    user_ids = data.get("notify_user_ids", [])
    product_name = data.get("product_name", "Producto")
    current_stock = data.get("current_stock", 0)
    _dispatch_for_event(
        "stock_low",
        f"Stock bajo: {product_name}",
        f"El producto '{product_name}' tiene stock en {current_stock} unidades, por debajo del mínimo.",
        user_ids,
    )


def on_quote_approved(data):
    """When a quote is approved, notify about potential expirations."""
    if not data or not isinstance(data, dict):
        return
    user_ids = data.get("notify_user_ids", [])
    quote_number = data.get("number", "N/A")
    _dispatch_for_event(
        "quote_expiration",
        f"Presupuesto {quote_number} aprobado",
        f"El presupuesto {quote_number} ha sido aprobado. Las cuotas están activas.",
        user_ids,
    )


def register_notification_subscribers():
    """Register all event bus subscribers for notifications."""
    event_bus.subscribe(Events.INVOICE_EMITTED, on_invoice_emitted, module="notifications")
    event_bus.subscribe(Events.STOCK_LOW, on_stock_low, module="notifications")
    event_bus.subscribe(Events.QUOTE_APPROVED, on_quote_approved, module="notifications")
    logger.info("🔔 Notification subscribers registered")
