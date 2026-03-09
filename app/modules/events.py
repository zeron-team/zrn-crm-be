"""
ZeRoN 360° — Event Bus
========================
Simple in-process event system for inter-module communication.
Modules can subscribe to events and emit them without tight coupling.

Usage:
    from app.modules.events import event_bus

    # Subscribe
    event_bus.subscribe("client.created", lambda data: print(data))

    # Emit
    event_bus.emit("client.created", {"id": 1, "name": "Acme"})
"""

import logging
from typing import Callable, Dict, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class EventBus:
    """Lightweight in-process event bus for module communication."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_log: List[dict] = []  # Last N events for debugging

    def subscribe(self, event: str, callback: Callable, module: str = "unknown"):
        """Subscribe a callback to an event."""
        self._subscribers[event].append(callback)
        logger.info(f"🔔 [{module}] subscribed to '{event}'")

    def emit(self, event: str, data: Any = None, source: str = "unknown"):
        """Emit an event to all subscribers."""
        subscribers = self._subscribers.get(event, [])
        logger.info(f"📡 Event '{event}' from [{source}] → {len(subscribers)} subscribers")

        # Keep last 100 events for debugging
        self._event_log.append({
            "event": event,
            "source": source,
            "subscribers": len(subscribers),
            "data_keys": list(data.keys()) if isinstance(data, dict) else str(type(data)),
        })
        if len(self._event_log) > 100:
            self._event_log = self._event_log[-100:]

        for callback in subscribers:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"❌ Event handler error for '{event}': {e}")

    def get_registered_events(self) -> Dict[str, int]:
        """Get all events and their subscriber counts."""
        return {event: len(subs) for event, subs in self._subscribers.items()}

    def get_recent_events(self, limit: int = 20) -> List[dict]:
        """Get recent event log for debugging."""
        return self._event_log[-limit:]


# Singleton event bus
event_bus = EventBus()


# ═══════════════════════════════════════════════════════════
# PREDEFINED EVENTS
# ═══════════════════════════════════════════════════════════

class Events:
    """Constants for standard event names."""
    # CRM
    CLIENT_CREATED = "client.created"
    CLIENT_UPDATED = "client.updated"
    CLIENT_DELETED = "client.deleted"
    LEAD_CREATED = "lead.created"
    LEAD_CONVERTED = "lead.converted"
    QUOTE_CREATED = "quote.created"
    QUOTE_APPROVED = "quote.approved"

    # ERP
    INVOICE_EMITTED = "invoice.emitted"
    INVOICE_PAID = "invoice.paid"
    PAYMENT_RECEIVED = "payment.received"
    STOCK_LOW = "stock.low"

    # HR
    EMPLOYEE_CREATED = "employee.created"
    PAYROLL_GENERATED = "payroll.generated"

    # System
    MODULE_ENABLED = "module.enabled"
    MODULE_DISABLED = "module.disabled"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    BACKUP_COMPLETED = "backup.completed"
