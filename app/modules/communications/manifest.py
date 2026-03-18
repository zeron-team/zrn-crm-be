"""
Communications Module — Email, WhatsApp, Notifications, Bot Flows.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import email as email_router
    from app.api.endpoints import whatsapp as whatsapp_router
    from app.api.endpoints import notifications
    from app.api.endpoints import notification_preferences
    from app.api.endpoints import bot_flow

    # Register event bus subscribers for notifications
    try:
        from app.services.notification_subscribers import register_notification_subscribers
        register_notification_subscribers()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not register notification subscribers: {e}")

    manifest = ModuleManifest(
        name="Comunicaciones",
        slug="communications",
        version="8.2.5",
        description="Email corporativo, WhatsApp integrado, notificaciones multi-canal, bot flows",
        icon="Mail",
        category="business",
        dependencies=["core"],
        routes=[
            (email_router.router, "", ["email"]),
            (whatsapp_router.router, "", ["whatsapp"]),
            (notifications.router, "", ["notifications"]),
            (notification_preferences.router, "", ["notification-preferences"]),
            (notification_preferences.logs_router, "", ["notification-logs"]),
            (bot_flow.router, "/bot-flows", ["bot-flows"]),
        ],
    )
    registry.register(manifest)


