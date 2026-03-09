"""
Core Module (Principal) — Always required.
Home, Dashboard, Notes, Calendar, AI Chat, Auth, Users.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import auth, users, dashboard_config, notes, calendar, ai_chat, dashboards

    manifest = ModuleManifest(
        name="Principal",
        slug="core",
        version="1.0.0",
        description="Módulo base: autenticación, usuarios, dashboard, notas, calendario, IA",
        icon="LayoutDashboard",
        category="core",
        dependencies=[],
        routes=[
            (auth.router, "/auth", ["auth"]),
            (users.router, "/users", ["users"]),
            (dashboard_config.router, "/dashboard-config", ["dashboard_config"]),
            (notes.router, "", ["notes"]),
            (calendar.router, "/calendar", ["calendar"]),
            (ai_chat.router, "/ai", ["ai"]),
            (dashboards.router, "", ["dashboards"]),
        ],
    )
    registry.register(manifest)
