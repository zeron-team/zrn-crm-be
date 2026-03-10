"""
Accounting Module — Períodos contables, asientos, obligaciones fiscales, dashboard contable.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import accounting

    manifest = ModuleManifest(
        name="Contabilidad",
        slug="accounting",
        version="1.0.0",
        description="Períodos contables, asientos, obligaciones fiscales y dashboard contable",
        icon="Calculator",
        category="business",
        dependencies=["core", "erp"],
        routes=[
            (accounting.router, "", ["accounting"]),
        ],
    )
    registry.register(manifest)
