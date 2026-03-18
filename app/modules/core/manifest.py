"""
Core Module (Principal) — Always required.
Home, Dashboard, Notes, Calendar, AI Chat, Auth, Users.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import auth, users, dashboard_config, notes, calendar, ai_chat, dashboards, profile, news

    manifest = ModuleManifest(
        name="Principal",
        slug="core",
        version="8.2.5",
        description="Módulo base: autenticación, usuarios, dashboard, notas, calendario, IA",
        icon="LayoutDashboard",
        category="core",
        dependencies=[],
        routes=[
            (auth.router, "/auth", ["auth"]),
            (profile.router, "/profile", ["profile"]),
            (users.router, "/users", ["users"]),
            (dashboard_config.router, "/dashboard-config", ["dashboard_config"]),
            (notes.router, "", ["notes"]),
            (calendar.router, "/calendar", ["calendar"]),
            (ai_chat.router, "/ai", ["ai"]),
            (dashboards.router, "", ["dashboards"]),
            (news.router, "", ["news"]),
        ],
    )
    registry.register(manifest)
