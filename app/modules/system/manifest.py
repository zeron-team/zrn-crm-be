"""
System Module — Settings, Audit, Roles, CompanySettings, System Status.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import (
        system as system_status,
        audit,
        role_configs,
        company_settings,
    )

    manifest = ModuleManifest(
        name="Sistema",
        slug="system",
        version="1.0.0",
        description="Configuración, seguridad, auditoría, roles y permisos",
        icon="Cog",
        category="core",
        dependencies=["core"],
        routes=[
            (system_status.router, "/system", ["system"]),
            (audit.router, "/audit", ["audit"]),
            (role_configs.router, "", ["role_configs"]),
            (company_settings.router, "", ["company_settings"]),
        ],
    )
    registry.register(manifest)
