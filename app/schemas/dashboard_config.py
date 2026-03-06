from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# Default widget set for new users
DEFAULT_WIDGETS = [
    "kpi_clients",
    "kpi_providers",
    "kpi_products",
    "kpi_users",
    "table_recent_invoices",
    "table_upcoming_events",
]

# Full catalog of available widgets
WIDGET_CATALOG = [
    # KPIs
    {"id": "kpi_clients", "type": "kpi", "label_key": "dashboard.widgets.kpi_clients"},
    {"id": "kpi_providers", "type": "kpi", "label_key": "dashboard.widgets.kpi_providers"},
    {"id": "kpi_products", "type": "kpi", "label_key": "dashboard.widgets.kpi_products"},
    {"id": "kpi_users", "type": "kpi", "label_key": "dashboard.widgets.kpi_users"},
    {"id": "kpi_invoices_issued", "type": "kpi", "label_key": "dashboard.widgets.kpi_invoices_issued"},
    {"id": "kpi_invoices_received", "type": "kpi", "label_key": "dashboard.widgets.kpi_invoices_received"},
    {"id": "kpi_leads", "type": "kpi", "label_key": "dashboard.widgets.kpi_leads"},
    {"id": "kpi_quotes", "type": "kpi", "label_key": "dashboard.widgets.kpi_quotes"},
    {"id": "kpi_active_services", "type": "kpi", "label_key": "dashboard.widgets.kpi_active_services"},
    {"id": "kpi_contacts", "type": "kpi", "label_key": "dashboard.widgets.kpi_contacts"},
    {"id": "kpi_categories", "type": "kpi", "label_key": "dashboard.widgets.kpi_categories"},
    {"id": "kpi_monthly_cost", "type": "kpi", "label_key": "dashboard.widgets.kpi_monthly_cost"},
    # Tables
    {"id": "table_recent_invoices", "type": "table", "label_key": "dashboard.widgets.table_recent_invoices"},
    {"id": "table_upcoming_events", "type": "table", "label_key": "dashboard.widgets.table_upcoming_events"},
    {"id": "table_recent_leads", "type": "table", "label_key": "dashboard.widgets.table_recent_leads"},
    {"id": "table_recent_quotes", "type": "table", "label_key": "dashboard.widgets.table_recent_quotes"},
    {"id": "table_service_payments", "type": "table", "label_key": "dashboard.widgets.table_service_payments"},
    {"id": "table_top_providers", "type": "table", "label_key": "dashboard.widgets.table_top_providers"},
    # Charts
    {"id": "chart_income_vs_expenses", "type": "chart", "label_key": "dashboard.widgets.chart_income_vs_expenses"},
    {"id": "chart_cashflow_distribution", "type": "chart", "label_key": "dashboard.widgets.chart_cashflow_distribution"},
    {"id": "chart_service_costs", "type": "chart", "label_key": "dashboard.widgets.chart_service_costs"},
    {"id": "chart_invoice_status", "type": "chart", "label_key": "dashboard.widgets.chart_invoice_status"},
]


class DashboardConfigBase(BaseModel):
    widgets: List[str]


class DashboardConfigCreate(DashboardConfigBase):
    pass


class DashboardConfigResponse(DashboardConfigBase):
    id: int
    user_id: int
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
