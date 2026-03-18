"""
Catalog Module — Products, Categories.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import products, categories

    manifest = ModuleManifest(
        name="Catálogo",
        slug="catalog",
        version="8.2.5",
        description="Catálogo de productos, servicios y mano de obra con categorías",
        icon="Package",
        category="business",
        dependencies=["core"],
        routes=[
            (products.router, "/products", ["products"]),
            (categories.router, "/categories", ["categories"]),
        ],
    )
    registry.register(manifest)
