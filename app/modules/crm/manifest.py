"""
CRM Module — Leads, Clients, Contacts, Quotes, Sellers, Tickets.
"""
from app.modules import ModuleManifest


def register(registry):
    from app.api.endpoints import (
        clients, leads, contacts, quotes, quote_installments,
        sellers, tickets, client_services,
    )

    manifest = ModuleManifest(
        name="CRM",
        slug="crm",
        version="8.2.5",
        description="Gestión comercial: leads, cuentas, contactos, presupuestos, soporte",
        icon="Briefcase",
        category="business",
        dependencies=["core"],
        routes=[
            (clients.router, "/clients", ["clients"]),
            (leads.router, "/leads", ["leads"]),
            (contacts.router, "/contacts", ["contacts"]),
            (quotes.router, "/quotes", ["quotes"]),
            (quote_installments.router, "/quotes", ["quote_installments"]),
            (sellers.router, "", ["sellers"]),
            (tickets.router, "/tickets", ["tickets"]),
            (client_services.router, "/client-services", ["client_services"]),
        ],
    )
    registry.register(manifest)
