from fastapi import APIRouter
from app.api.endpoints import users, clients, providers, products, contacts, invoices, calendar, client_services, provider_services
from app.api.endpoints import leads, quotes, auth, dashboard_config, categories, service_payments, arca, tickets, quote_installments
from app.api.endpoints import delivery_notes, payment_orders, purchase_orders, inventory, warehouses, dashboards, exchange_rates
from app.api.endpoints import email as email_router
from app.api.endpoints import whatsapp as whatsapp_router
from app.api.endpoints import notes
from app.api.endpoints import projects
from app.api.endpoints import notifications
from app.api.endpoints import wiki
from app.api.endpoints import sellers
from app.api.endpoints import employees
from app.api.endpoints import time_entries
from app.api.endpoints import role_configs
from app.api.endpoints import payroll
from app.api.endpoints import company_settings
from app.api.endpoints import ai_chat
from app.api.endpoints import audit
from app.api.endpoints import system as system_status

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
api_router.include_router(calendar.router, prefix="/calendar", tags=["calendar"])
api_router.include_router(client_services.router, prefix="/client-services", tags=["client_services"])
api_router.include_router(provider_services.router, prefix="/provider-services", tags=["provider_services"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["quotes"])
api_router.include_router(dashboard_config.router, prefix="/dashboard-config", tags=["dashboard_config"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(service_payments.router)
api_router.include_router(arca.router, prefix="/arca", tags=["arca"])
api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(quote_installments.router, prefix="/quotes", tags=["quote_installments"])
api_router.include_router(delivery_notes.router)
api_router.include_router(payment_orders.router)
api_router.include_router(purchase_orders.router)
api_router.include_router(inventory.router)
api_router.include_router(warehouses.router)
api_router.include_router(dashboards.router)
api_router.include_router(exchange_rates.router)
api_router.include_router(email_router.router)
api_router.include_router(whatsapp_router.router)
api_router.include_router(notes.router)
api_router.include_router(projects.router)
api_router.include_router(notifications.router)
api_router.include_router(wiki.router)
api_router.include_router(sellers.router)
api_router.include_router(employees.router)
api_router.include_router(time_entries.router)
api_router.include_router(role_configs.router)
api_router.include_router(payroll.router)
api_router.include_router(company_settings.router)
api_router.include_router(ai_chat.router, prefix="/ai", tags=["ai"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(system_status.router, prefix="/system", tags=["system"])

from app.api.endpoints import employee_novelties
api_router.include_router(employee_novelties.router)


