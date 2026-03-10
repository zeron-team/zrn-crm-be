"""
ERP Module — Invoices, ARCA, DeliveryNotes, PurchaseOrders,
Inventory, Warehouses, ExchangeRates, ServicePurchases, ProviderServices.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import (
        invoices, arca, delivery_notes, payment_orders,
        purchase_orders, inventory, warehouses, exchange_rates,
        service_payments, provider_services, providers,
        accounting,
    )

    manifest = ModuleManifest(
        name="ERP",
        slug="erp",
        version="1.0.0",
        description="Facturación, ARCA/AFIP, remitos, inventario, depósitos, tipo de cambio",
        icon="Receipt",
        category="business",
        dependencies=["core", "crm"],
        routes=[
            (invoices.router, "/invoices", ["invoices"]),
            (arca.router, "/arca", ["arca"]),
            (providers.router, "/providers", ["providers"]),
            (delivery_notes.router, "", ["delivery_notes"]),
            (payment_orders.router, "", ["payment_orders"]),
            (purchase_orders.router, "", ["purchase_orders"]),
            (inventory.router, "", ["inventory"]),
            (warehouses.router, "", ["warehouses"]),
            (exchange_rates.router, "", ["exchange_rates"]),
            (service_payments.router, "", ["service_payments"]),
            (provider_services.router, "/provider-services", ["provider_services"]),
            (accounting.router, "", ["accounting"]),
        ],
    )
    registry.register(manifest)
