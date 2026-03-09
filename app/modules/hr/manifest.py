"""
HR Module (RRHH) — Employees, Time Tracking, Payroll.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import employees, time_entries, payroll

    manifest = ModuleManifest(
        name="RRHH",
        slug="hr",
        version="1.0.0",
        description="Recursos Humanos: empleados, fichadas, liquidación de sueldos",
        icon="UserCheck",
        category="business",
        dependencies=["core"],
        routes=[
            (employees.router, "", ["employees"]),
            (time_entries.router, "", ["time_entries"]),
            (payroll.router, "", ["payroll"]),
        ],
    )
    registry.register(manifest)
