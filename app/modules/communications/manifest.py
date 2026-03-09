"""
Communications Module — Email, WhatsApp, Notifications.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import email as email_router
    from app.api.endpoints import whatsapp as whatsapp_router
    from app.api.endpoints import notifications

    manifest = ModuleManifest(
        name="Comunicaciones",
        slug="communications",
        version="1.0.0",
        description="Email corporativo, WhatsApp integrado, notificaciones",
        icon="Mail",
        category="business",
        dependencies=["core"],
        routes=[
            (email_router.router, "", ["email"]),
            (whatsapp_router.router, "", ["whatsapp"]),
            (notifications.router, "", ["notifications"]),
        ],
    )
    registry.register(manifest)
