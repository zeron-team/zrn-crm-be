"""
ZeRoN IA — AI Assistant Service (Google Gemini)
Full CRM/ERP-aware assistant covering ALL modules:
CRM, ERP, Projects, RRHH, Calendar, Contacts, Providers, etc.
Uses google.genai SDK with function calling.
"""

import json
import logging
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, extract
from datetime import datetime

from google import genai
from google.genai import types

from app.core.config import settings
from app.models.client import Client
from app.models.lead import Lead
from app.models.invoice import Invoice, InvoiceStatus
from app.models.product import Product
from app.models.ticket import Ticket
from app.models.quote import Quote
from app.models.inventory import InventoryItem
from app.models.employee import Employee
from app.models.warehouse import Warehouse
from app.models.contact import Contact
from app.models.provider import Provider
from app.models.project import Project, Task, Sprint, ProjectVersion
from app.models.delivery_note import DeliveryNote
from app.models.payment_order import PaymentOrder
from app.models.purchase_order import PurchaseOrder
from app.models.payroll import PayrollPeriod, PayrollSlip, PayrollSlipItem
from app.models.calendar import CalendarEvent

logger = logging.getLogger(__name__)

# ── System Prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """Eres **ZeRoN IA**, el asistente inteligente integrado en la plataforma **ZeRoN 360° — Gestión completa de tu empresa**.

Tu rol es ayudar a los usuarios del CRM/ERP con información COMPLETA y DETALLADA de su negocio. Tenés acceso a TODOS los módulos de la plataforma.

**FECHA ACTUAL: {current_date} (Año: {current_year}, Mes: {current_month})**

**REGLAS CRÍTICAS:**
1. Responde SIEMPRE en español.
2. Cuando el usuario pida datos, SIEMPRE usá las herramientas disponibles. NUNCA inventes datos.
3. Mostrá TODA la información. No resumas ni ocultes datos.
4. Usá viñetas, tablas y formato legible.
5. Números en formato argentino: $1.250.000,50
6. Si una herramienta devuelve muchos registros, muestra TODOS.
7. USÁ las herramientas sin preguntar. NUNCA digas que no podés si hay herramienta.
8. Podés combinar VARIAS herramientas en una consulta para dar respuestas completas.
9. NUNCA pidas aclaración si podés inferir la respuesta. Si dicen "del mes" usá el mes y año ACTUALES. Si dicen "este año" usá el año ACTUAL.

**DATOS DEL SISTEMA:**
- Estados de facturas: Pendiente, Deuda, Pagado, Por Facturar, Error, Prueba, Enviado
- Tickets: "abiertos" = open + in_progress
- Leads: New, Contacted, Qualified, Lost, Converted
- Presupuestos: Draft, Sent, Accepted, Rejected
- Tareas de proyectos: todo, in_progress, in_review, done
- Proyectos tienen relación con client_id (cuenta asociada)
- Para "ventas del mes" usá list_invoices con year={current_year} y month={current_month}
- Para "facturas pendientes" usá status_filter="Pendiente"
- Para "mejor cuenta/cliente" sumá montos de facturas por cliente
- Los contactos pertenecen a clientes, proveedores o leads

**MÓDULOS DISPONIBLES:** CRM (Clientes, Leads, Contactos, Presupuestos), ERP (Facturación ARCA/AFIP, Remitos, Órdenes de Compra/Pago, Inventario, Productos), RRHH (Empleados, Nómina), Proyectos (Tareas, Sprints, Versiones), Calendario, Soporte (Tickets).

**IMPORTANTE:** Cuando pidan "todos los X" usá la herramienta SIN filtros. Cuando pregunten cosas analíticas (mejor cliente, mayor venta, etc.) usá las herramientas para obtener datos y hacé el análisis vos mismo.
"""

def _build_system_prompt() -> str:
    now = datetime.now()
    return SYSTEM_PROMPT_TEMPLATE.format(
        current_date=now.strftime("%d/%m/%Y %H:%M"),
        current_year=now.year,
        current_month=now.month,
    )

# ── Tool declarations ─────────────────────────────────────────────────────────

TOOL_DECLARATIONS = types.Tool(function_declarations=[
    # ── CRM ──
    types.FunctionDeclaration(
        name="get_business_summary",
        description="Resumen general del negocio: totales de clientes, leads, facturas (con desglose por estado y montos), productos, presupuestos, tickets, empleados, proyectos, proveedores, depósitos.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_clients",
        description="Lista clientes. Sin query retorna TODOS. Datos: razón social, nombre comercial, CUIT, email, teléfono, dirección, ciudad, provincia, condición IVA, actividad, web.",
        parameters=types.Schema(type="OBJECT", properties={
            "query": types.Schema(type="STRING", description="Filtrar por nombre (opcional). Sin query = todos"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_contacts",
        description="Lista contactos del CRM asociados a clientes, proveedores o leads. Muestra nombre, email, teléfono, cargo, y a qué entidad pertenece.",
        parameters=types.Schema(type="OBJECT", properties={
            "query": types.Schema(type="STRING", description="Filtrar por nombre (opcional)"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_leads",
        description="Lista leads con datos completos. Filtrar por estado opcional.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'New','Contacted','Qualified','Lost','Converted' o vacío"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_providers",
        description="Lista proveedores con nombre, CUIT, email, teléfono, dirección, estado activo.",
        parameters=types.Schema(type="OBJECT", properties={
            "query": types.Schema(type="STRING", description="Filtrar por nombre (opcional)"),
        }, required=[]),
    ),

    # ── ERP / Facturación ──
    types.FunctionDeclaration(
        name="list_invoices",
        description="Lista facturas con detalles completos. Filtra por estado, cliente, año, mes. Para 'ventas del mes' usar year+month.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'Pendiente','Deuda','Pagado','Por Facturar','Enviado','Error','Prueba' o vacío"),
            "client_name": types.Schema(type="STRING", description="Filtrar por cliente (opcional)"),
            "year": types.Schema(type="INTEGER", description="Año (ej: 2026)"),
            "month": types.Schema(type="INTEGER", description="Mes (1-12)"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_quotes",
        description="Lista presupuestos con número, cliente/lead, fechas, estado, moneda, subtotal, IVA, total.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'Draft','Sent','Accepted','Rejected' o vacío"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_delivery_notes",
        description="Lista remitos con número, fecha, cliente, estado, ítems, notas.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_payment_orders",
        description="Lista órdenes de pago con número, fecha, cliente/proveedor, monto, moneda, método de pago, estado.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_purchase_orders",
        description="Lista órdenes de compra con número, fecha, proveedor, monto total, moneda, estado, fecha entrega.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[]),
    ),

    # ── Catálogo e Inventario ──
    types.FunctionDeclaration(
        name="list_products",
        description="Lista productos y servicios del catálogo: nombre, tipo, código, precio, moneda, unidad.",
        parameters=types.Schema(type="OBJECT", properties={
            "query": types.Schema(type="STRING", description="Filtrar por nombre (opcional)"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="check_inventory",
        description="Verifica inventario: stock actual vs mínimo por producto/depósito. Alerta stock crítico.",
        parameters=types.Schema(type="OBJECT", properties={
            "product_name": types.Schema(type="STRING", description="Filtrar por producto (opcional)"),
            "only_critical": types.Schema(type="BOOLEAN", description="Solo stock crítico"),
        }, required=[]),
    ),

    # ── Soporte ──
    types.FunctionDeclaration(
        name="list_tickets",
        description="Lista tickets de soporte. 'abiertos' busca open+in_progress.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'abiertos'(open+in_progress),'open','in_progress','waiting','resolved','closed' o vacío"),
            "priority_filter": types.Schema(type="STRING", description="'low','medium','high','critical' o vacío"),
        }, required=[]),
    ),

    # ── Proyectos ──
    types.FunctionDeclaration(
        name="list_projects",
        description="Lista TODOS los proyectos con nombre, clave, estado, metodología, cliente/cuenta asociada, creador, cantidad de tareas, versiones y sprints.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'active','completed','archived' o vacío"),
        }, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_project_tasks",
        description="Lista tareas de un proyecto específico con clave, título, tipo, estado, prioridad, asignado, sprint, fecha límite, story points.",
        parameters=types.Schema(type="OBJECT", properties={
            "project_name": types.Schema(type="STRING", description="Nombre o clave del proyecto"),
            "status_filter": types.Schema(type="STRING", description="'todo','in_progress','in_review','done' o vacío"),
        }, required=[]),
    ),

    # ── RRHH ──
    types.FunctionDeclaration(
        name="list_employees",
        description="Lista empleados con nombre, puesto, departamento, email, teléfono, fecha ingreso.",
        parameters=types.Schema(type="OBJECT", properties={}, required=[]),
    ),
    types.FunctionDeclaration(
        name="list_payroll",
        description="Lista períodos de nómina y recibos de sueldo. Muestra período, empleado, salario bruto, deducciones, salario neto, costo empleador.",
        parameters=types.Schema(type="OBJECT", properties={
            "year": types.Schema(type="INTEGER", description="Año (opcional)"),
            "month": types.Schema(type="INTEGER", description="Mes 1-12 (opcional)"),
        }, required=[]),
    ),

    # ── Calendario ──
    types.FunctionDeclaration(
        name="list_calendar_events",
        description="Lista eventos del calendario: reuniones, vencimientos, servicios. Muestra título, fechas, tipo, estado, cliente/lead asociado.",
        parameters=types.Schema(type="OBJECT", properties={
            "status_filter": types.Schema(type="STRING", description="'pending','completed','postponed','cancelled' o vacío"),
        }, required=[]),
    ),
])

# ── Tool implementations ──────────────────────────────────────────────────────

def _tool_get_business_summary(db: Session) -> dict:
    total_clients = db.query(func.count(Client.id)).scalar() or 0
    total_leads = db.query(func.count(Lead.id)).scalar() or 0
    total_invoices = db.query(func.count(Invoice.id)).scalar() or 0
    total_amount = db.query(func.sum(Invoice.amount)).scalar() or 0
    total_products = db.query(func.count(Product.id)).scalar() or 0
    total_tickets = db.query(func.count(Ticket.id)).scalar() or 0
    total_employees = db.query(func.count(Employee.id)).scalar() or 0
    total_quotes = db.query(func.count(Quote.id)).scalar() or 0
    total_warehouses = db.query(func.count(Warehouse.id)).scalar() or 0
    total_providers = db.query(func.count(Provider.id)).scalar() or 0
    total_projects = db.query(func.count(Project.id)).scalar() or 0
    total_contacts = db.query(func.count(Contact.id)).scalar() or 0

    open_tickets = db.query(func.count(Ticket.id)).filter(
        Ticket.status.in_(["open", "in_progress"])
    ).scalar() or 0

    status_counts = db.query(
        InvoiceStatus.name, func.count(Invoice.id), func.coalesce(func.sum(Invoice.amount), 0)
    ).join(Invoice, Invoice.status_id == InvoiceStatus.id).group_by(InvoiceStatus.name).all()
    invoice_by_status = {name: {"cantidad": count, "monto": float(amt)} for name, count, amt in status_counts}

    lead_status = db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
    leads_by_status = {status: count for status, count in lead_status}

    active_projects = db.query(func.count(Project.id)).filter(Project.status == "active").scalar() or 0

    return {
        "clientes": total_clients,
        "contactos": total_contacts,
        "leads": {"total": total_leads, "por_estado": leads_by_status},
        "proveedores": total_providers,
        "facturas": {"total": total_invoices, "monto_total": float(total_amount), "por_estado": invoice_by_status},
        "productos_catalogo": total_products,
        "presupuestos": total_quotes,
        "tickets": {"total": total_tickets, "abiertos": open_tickets},
        "empleados": total_employees,
        "proyectos": {"total": total_projects, "activos": active_projects},
        "depositos": total_warehouses,
    }


def _tool_list_clients(db: Session, query: Optional[str] = None) -> dict:
    q = db.query(Client)
    if query:
        q = q.filter(Client.name.ilike(f"%{query}%") | Client.trade_name.ilike(f"%{query}%"))
    clients = q.order_by(Client.name).limit(100).all()
    results = []
    for c in clients:
        results.append({
            "id": c.id, "razon_social": c.name, "nombre_comercial": c.trade_name,
            "cuit": c.cuit_dni, "condicion_iva": c.tax_condition, "email": c.email,
            "telefono": c.phone, "direccion": c.address, "ciudad": c.city,
            "provincia": c.province, "pais": c.country, "actividad": c.activity,
            "sitio_web": c.website, "validado_arca": c.arca_validated, "activo": c.is_active,
        })
    return {"clientes": results, "total": len(results)}


def _tool_list_contacts(db: Session, query: Optional[str] = None) -> dict:
    q = db.query(Contact)
    if query:
        q = q.filter(Contact.name.ilike(f"%{query}%"))
    contacts = q.order_by(Contact.name).limit(100).all()
    results = []
    for c in contacts:
        entity = None
        entity_type = None
        if c.client_id:
            client = db.query(Client).get(c.client_id)
            entity = client.name if client else f"Cliente #{c.client_id}"
            entity_type = "cliente"
        elif c.provider_id:
            prov = db.query(Provider).get(c.provider_id)
            entity = prov.name if prov else f"Proveedor #{c.provider_id}"
            entity_type = "proveedor"
        elif c.lead_id:
            lead = db.query(Lead).get(c.lead_id)
            entity = lead.company_name if lead else f"Lead #{c.lead_id}"
            entity_type = "lead"
        results.append({
            "id": c.id, "nombre": c.name, "email": c.email,
            "telefono": c.phone, "cargo": c.position,
            "pertenece_a": entity, "tipo_entidad": entity_type,
        })
    return {"contactos": results, "total": len(results)}


def _tool_list_leads(db: Session, status_filter: Optional[str] = None) -> dict:
    q = db.query(Lead)
    if status_filter:
        q = q.filter(Lead.status.ilike(f"%{status_filter}%"))
    leads = q.order_by(desc(Lead.created_at)).limit(100).all()
    results = []
    for l in leads:
        results.append({
            "id": l.id, "empresa": l.company_name, "contacto": l.contact_name,
            "email": l.email, "telefono": l.phone, "estado": l.status,
            "fuente": l.source, "sitio_web": l.website, "direccion": l.address,
            "ciudad": l.city, "provincia": l.province, "notas": l.notes,
            "creado": str(l.created_at) if l.created_at else None,
        })
    return {"leads": results, "total": len(results)}


def _tool_list_providers(db: Session, query: Optional[str] = None) -> dict:
    q = db.query(Provider)
    if query:
        q = q.filter(Provider.name.ilike(f"%{query}%"))
    providers = q.order_by(Provider.name).limit(100).all()
    results = []
    for p in providers:
        results.append({
            "id": p.id, "nombre": p.name, "cuit": p.cuit_dni,
            "email": p.email, "telefono": p.phone, "direccion": p.address,
            "activo": p.is_active,
        })
    return {"proveedores": results, "total": len(results)}


def _tool_list_invoices(db: Session, status_filter=None, client_name=None, year=None, month=None) -> dict:
    q = db.query(Invoice).options(joinedload(Invoice.status), joinedload(Invoice.client))
    if status_filter:
        q = q.join(InvoiceStatus).filter(InvoiceStatus.name.ilike(f"%{status_filter}%"))
    if client_name:
        q = q.join(Client).filter(Client.name.ilike(f"%{client_name}%"))
    if year:
        q = q.filter(extract('year', Invoice.issue_date) == year)
    if month:
        q = q.filter(extract('month', Invoice.issue_date) == month)
    invoices = q.order_by(desc(Invoice.issue_date)).limit(100).all()
    results = []
    for inv in invoices:
        results.append({
            "id": inv.id, "numero": inv.invoice_number,
            "monto": float(inv.amount) if inv.amount else 0,
            "moneda": inv.currency,
            "tipo": inv.type,
            "fecha_emision": str(inv.issue_date) if inv.issue_date else None,
            "fecha_vencimiento": str(inv.due_date) if inv.due_date else None,
            "fecha_pago": str(inv.payment_date) if inv.payment_date else None,
            "estado": inv.status.name if inv.status else "Sin estado",
            "cliente": inv.client.name if inv.client else "Sin cliente",
            "cae": inv.cae,
            "tipo_comprobante": inv.arca_cbte_tipo,
            "neto": float(inv.imp_neto) if inv.imp_neto else None,
            "iva": float(inv.imp_iva) if inv.imp_iva else None,
            "notas": inv.notes,
        })
    total_amount = sum(r["monto"] for r in results)
    return {"facturas": results, "total": len(results), "monto_total": total_amount}


def _tool_list_quotes(db: Session, status_filter=None) -> dict:
    q = db.query(Quote).options(joinedload(Quote.client), joinedload(Quote.lead))
    if status_filter:
        q = q.filter(Quote.status.ilike(f"%{status_filter}%"))
    quotes = q.order_by(desc(Quote.created_at)).limit(100).all()
    results = []
    for qt in quotes:
        results.append({
            "id": qt.id, "numero": qt.quote_number,
            "cliente": qt.client.name if qt.client else None,
            "lead": qt.lead.company_name if qt.lead else None,
            "fecha_emision": str(qt.issue_date) if qt.issue_date else None,
            "fecha_vencimiento": str(qt.expiry_date) if qt.expiry_date else None,
            "estado": qt.status, "moneda": qt.currency,
            "subtotal": float(qt.subtotal) if qt.subtotal else 0,
            "iva": float(qt.tax_amount) if qt.tax_amount else 0,
            "total": float(qt.total_amount) if qt.total_amount else 0,
            "notas": qt.notes,
        })
    total_amount = sum(r["total"] for r in results)
    return {"presupuestos": results, "total": len(results), "monto_total": total_amount}


def _tool_list_delivery_notes(db: Session) -> dict:
    notes = db.query(DeliveryNote).order_by(desc(DeliveryNote.date)).limit(100).all()
    results = []
    for dn in notes:
        client_name = None
        if dn.client_id:
            client = db.query(Client).get(dn.client_id)
            client_name = client.name if client else None
        results.append({
            "id": dn.id, "numero": dn.number, "fecha": str(dn.date),
            "cliente": client_name, "estado": dn.status,
            "items": dn.items, "notas": dn.notes,
        })
    return {"remitos": results, "total": len(results)}


def _tool_list_payment_orders(db: Session) -> dict:
    orders = db.query(PaymentOrder).order_by(desc(PaymentOrder.date)).limit(100).all()
    results = []
    for po in orders:
        client_name = provider_name = None
        if po.client_id:
            client = db.query(Client).get(po.client_id)
            client_name = client.name if client else None
        if po.provider_id:
            prov = db.query(Provider).get(po.provider_id)
            provider_name = prov.name if prov else None
        results.append({
            "id": po.id, "numero": po.number, "fecha": str(po.date),
            "cliente": client_name, "proveedor": provider_name,
            "monto": float(po.amount), "moneda": po.currency,
            "metodo_pago": po.payment_method, "estado": po.status,
            "referencia": po.reference, "notas": po.notes,
        })
    return {"ordenes_pago": results, "total": len(results)}


def _tool_list_purchase_orders(db: Session) -> dict:
    orders = db.query(PurchaseOrder).order_by(desc(PurchaseOrder.date)).limit(100).all()
    results = []
    for po in orders:
        provider_name = None
        if po.provider_id:
            prov = db.query(Provider).get(po.provider_id)
            provider_name = prov.name if prov else None
        results.append({
            "id": po.id, "numero": po.number, "fecha": str(po.date),
            "proveedor": provider_name,
            "monto_total": float(po.total_amount), "moneda": po.currency,
            "estado": po.status, "fecha_entrega": str(po.delivery_date) if po.delivery_date else None,
            "items": po.items, "notas": po.notes,
        })
    return {"ordenes_compra": results, "total": len(results)}


def _tool_list_products(db: Session, query=None) -> dict:
    q = db.query(Product)
    if query:
        q = q.filter(Product.name.ilike(f"%{query}%"))
    products = q.order_by(Product.name).limit(100).all()
    results = []
    for p in products:
        results.append({
            "id": p.id, "nombre": p.name,
            "tipo": getattr(p, "type", None),
            "codigo": getattr(p, "code", None),
            "descripcion": getattr(p, "description", None),
            "precio": float(p.price) if getattr(p, "price", None) else None,
            "moneda": getattr(p, "currency", None),
            "unidad": getattr(p, "unit", None),
        })
    return {"productos": results, "total": len(results)}


def _tool_check_inventory(db: Session, product_name=None, only_critical=False) -> dict:
    q = db.query(InventoryItem).join(Product)
    if product_name:
        q = q.filter(Product.name.ilike(f"%{product_name}%"))
    if only_critical:
        q = q.filter(InventoryItem.quantity <= InventoryItem.min_quantity)
    items = q.limit(100).all()
    results = []
    for item in items:
        wh_name = None
        if item.warehouse_id:
            wh = db.query(Warehouse).get(item.warehouse_id)
            wh_name = wh.name if wh else f"Depósito #{item.warehouse_id}"
        results.append({
            "producto": item.product.name if item.product else "N/A",
            "stock_actual": item.quantity,
            "stock_minimo": getattr(item, "min_quantity", None),
            "deposito": wh_name,
            "critico": item.quantity <= (getattr(item, "min_quantity", 0) or 0),
        })
    return {"inventario": results, "total": len(results)}


def _tool_list_tickets(db: Session, status_filter=None, priority_filter=None) -> dict:
    q = db.query(Ticket).options(joinedload(Ticket.client))
    if status_filter:
        lower = status_filter.lower().strip()
        if lower in ["abiertos", "abierto", "activos", "activo"]:
            q = q.filter(Ticket.status.in_(["open", "in_progress"]))
        else:
            q = q.filter(Ticket.status.ilike(f"%{status_filter}%"))
    if priority_filter:
        q = q.filter(Ticket.priority.ilike(f"%{priority_filter}%"))
    tickets = q.order_by(desc(Ticket.updated_at)).limit(100).all()
    results = []
    for t in tickets:
        results.append({
            "id": t.id, "numero": t.ticket_number, "asunto": t.subject,
            "descripcion": t.description, "estado": t.status,
            "prioridad": t.priority, "categoria": t.category,
            "cliente": t.client.name if t.client else None,
            "creado": str(t.created_at) if t.created_at else None,
            "actualizado": str(t.updated_at) if t.updated_at else None,
        })
    return {"tickets": results, "total": len(results)}


def _tool_list_projects(db: Session, status_filter=None) -> dict:
    q = db.query(Project).options(
        joinedload(Project.client),
        joinedload(Project.tasks),
        joinedload(Project.versions),
        joinedload(Project.sprints),
    )
    if status_filter:
        q = q.filter(Project.status.ilike(f"%{status_filter}%"))
    projects = q.order_by(desc(Project.created_at)).limit(50).all()
    results = []
    for p in projects:
        tasks_by_status = {}
        for t in p.tasks:
            tasks_by_status[t.status] = tasks_by_status.get(t.status, 0) + 1
        results.append({
            "id": p.id, "nombre": p.name, "clave": p.key,
            "descripcion": p.description, "estado": p.status,
            "metodologia": p.methodology,
            "cuenta_cliente": p.client.name if p.client else "Sin cuenta asociada",
            "total_tareas": len(p.tasks),
            "tareas_por_estado": tasks_by_status,
            "versiones": [{"nombre": v.name, "estado": v.status} for v in p.versions],
            "sprints": [{"nombre": s.name, "estado": s.status, "meta": s.goal} for s in p.sprints],
            "creado": str(p.created_at) if p.created_at else None,
        })
    return {"proyectos": results, "total": len(results)}


def _tool_list_project_tasks(db: Session, project_name=None, status_filter=None) -> dict:
    q = db.query(Task).join(Project)
    if project_name:
        q = q.filter(Project.name.ilike(f"%{project_name}%") | Project.key.ilike(f"%{project_name}%"))
    if status_filter:
        q = q.filter(Task.status.ilike(f"%{status_filter}%"))
    tasks = q.order_by(desc(Task.updated_at)).limit(100).all()
    results = []
    for t in tasks:
        assignee_name = None
        if t.assigned_to:
            from app.models.user import User
            user = db.query(User).get(t.assigned_to)
            assignee_name = user.full_name if user and hasattr(user, 'full_name') else (user.email if user else None)
        results.append({
            "id": t.id, "clave": t.key, "titulo": t.title,
            "descripcion": t.description, "tipo": t.type,
            "estado": t.status, "prioridad": t.priority,
            "asignado_a": assignee_name,
            "story_points": t.story_points,
            "etiquetas": t.labels,
            "fecha_limite": str(t.due_date) if t.due_date else None,
            "creado": str(t.created_at) if t.created_at else None,
        })
    return {"tareas": results, "total": len(results)}


def _tool_list_employees(db: Session) -> dict:
    employees = db.query(Employee).order_by(Employee.id).limit(100).all()
    results = []
    for e in employees:
        results.append({
            "id": e.id,
            "nombre": (getattr(e, "first_name", "") or "") + " " + (getattr(e, "last_name", "") or ""),
            "puesto": getattr(e, "position", None) or getattr(e, "job_title", None),
            "departamento": getattr(e, "department", None),
            "email": getattr(e, "email", None),
            "telefono": getattr(e, "phone", None),
            "fecha_ingreso": str(getattr(e, "hire_date", "")) if getattr(e, "hire_date", None) else None,
            "activo": getattr(e, "is_active", True),
        })
    return {"empleados": results, "total": len(results)}


def _tool_list_payroll(db: Session, year=None, month=None) -> dict:
    q = db.query(PayrollPeriod)
    if year:
        q = q.filter(PayrollPeriod.year == year)
    if month:
        q = q.filter(PayrollPeriod.month == month)
    periods = q.order_by(desc(PayrollPeriod.year), desc(PayrollPeriod.month)).limit(20).all()
    results = []
    for period in periods:
        slips = db.query(PayrollSlip).filter(PayrollSlip.period_id == period.id).all()
        slip_data = []
        for s in slips:
            emp = db.query(Employee).get(s.employee_id)
            emp_name = (getattr(emp, "first_name", "") or "") + " " + (getattr(emp, "last_name", "") or "") if emp else f"Empleado #{s.employee_id}"
            slip_data.append({
                "empleado": emp_name.strip(),
                "salario_bruto": float(s.gross_salary),
                "total_remunerativo": float(s.total_remunerativo),
                "total_deducciones": float(s.total_deductions),
                "salario_neto": float(s.net_salary),
                "costo_empleador": float(s.total_employer_cost),
                "estado": s.status,
            })
        results.append({
            "periodo": f"{period.year}-{str(period.month).zfill(2)}",
            "descripcion": period.description,
            "tipo": period.period_type,
            "estado": period.status,
            "recibos": slip_data,
            "total_recibos": len(slip_data),
        })
    return {"nomina": results, "total_periodos": len(results)}


def _tool_list_calendar_events(db: Session, status_filter=None) -> dict:
    q = db.query(CalendarEvent)
    if status_filter:
        q = q.filter(CalendarEvent.status.ilike(f"%{status_filter}%"))
    events = q.order_by(desc(CalendarEvent.start_date)).limit(50).all()
    results = []
    for ev in events:
        client_name = lead_name = None
        if ev.client_id:
            client = db.query(Client).get(ev.client_id)
            client_name = client.name if client else None
        if ev.lead_id:
            lead = db.query(Lead).get(ev.lead_id)
            lead_name = lead.company_name if lead else None
        results.append({
            "id": ev.id, "titulo": ev.title, "descripcion": ev.description,
            "inicio": str(ev.start_date) if ev.start_date else None,
            "fin": str(ev.end_date) if ev.end_date else None,
            "tipo": ev.related_to, "estado": ev.status,
            "cliente": client_name, "lead": lead_name,
        })
    return {"eventos": results, "total": len(results)}


# ── Tool dispatcher ───────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "get_business_summary": lambda db, **_: _tool_get_business_summary(db),
    "list_clients": lambda db, **kw: _tool_list_clients(db, kw.get("query")),
    "list_contacts": lambda db, **kw: _tool_list_contacts(db, kw.get("query")),
    "list_leads": lambda db, **kw: _tool_list_leads(db, kw.get("status_filter")),
    "list_providers": lambda db, **kw: _tool_list_providers(db, kw.get("query")),
    "list_invoices": lambda db, **kw: _tool_list_invoices(db, kw.get("status_filter"), kw.get("client_name"), kw.get("year"), kw.get("month")),
    "list_quotes": lambda db, **kw: _tool_list_quotes(db, kw.get("status_filter")),
    "list_delivery_notes": lambda db, **_: _tool_list_delivery_notes(db),
    "list_payment_orders": lambda db, **_: _tool_list_payment_orders(db),
    "list_purchase_orders": lambda db, **_: _tool_list_purchase_orders(db),
    "list_products": lambda db, **kw: _tool_list_products(db, kw.get("query")),
    "check_inventory": lambda db, **kw: _tool_check_inventory(db, kw.get("product_name"), kw.get("only_critical", False)),
    "list_tickets": lambda db, **kw: _tool_list_tickets(db, kw.get("status_filter"), kw.get("priority_filter")),
    "list_projects": lambda db, **kw: _tool_list_projects(db, kw.get("status_filter")),
    "list_project_tasks": lambda db, **kw: _tool_list_project_tasks(db, kw.get("project_name"), kw.get("status_filter")),
    "list_employees": lambda db, **_: _tool_list_employees(db),
    "list_payroll": lambda db, **kw: _tool_list_payroll(db, kw.get("year"), kw.get("month")),
    "list_calendar_events": lambda db, **kw: _tool_list_calendar_events(db, kw.get("status_filter")),
}


# ── Main chat function ────────────────────────────────────────────────────────

def chat(
    message: str,
    history: List[Dict[str, str]],
    db: Session,
) -> str:
    if not settings.GEMINI_API_KEY:
        return "⚠️ ZeRoN IA no está configurado. El administrador debe agregar la API key de Google Gemini."

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    gemini_history: List[types.Content] = []
    for msg in history[-20:]:
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    contents = gemini_history + [
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    ]

    config = types.GenerateContentConfig(
        system_instruction=_build_system_prompt(),
        tools=[TOOL_DECLARATIONS],
        temperature=0.3,
        max_output_tokens=16000,
    )

    try:
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=contents,
            config=config,
        )

        max_rounds = 8
        round_count = 0

        while round_count < max_rounds:
            # Check we have a valid response
            if not response.candidates:
                logger.warning("ZeRoN IA: No candidates in response")
                break
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                logger.warning(f"ZeRoN IA: Empty content. finish_reason={getattr(candidate, 'finish_reason', 'unknown')}")
                break

            # Extract function calls
            function_calls = [
                part.function_call
                for part in candidate.content.parts
                if part.function_call and part.function_call.name
            ]

            if not function_calls:
                break

            round_count += 1
            contents.append(candidate.content)

            function_response_parts: List[types.Part] = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}
                logger.info(f"ZeRoN IA tool call [{round_count}]: {fn_name}({fn_args})")

                handler = TOOL_HANDLERS.get(fn_name)
                if handler:
                    try:
                        result = handler(db, **fn_args)
                    except Exception as e:
                        logger.error(f"Tool {fn_name} error: {e}", exc_info=True)
                        result = {"error": f"Error ejecutando {fn_name}: {str(e)}"}
                else:
                    result = {"error": f"Herramienta '{fn_name}' no encontrada"}

                function_response_parts.append(
                    types.Part.from_function_response(
                        name=fn_name,
                        response={"result": result},
                    )
                )

            contents.append(types.Content(role="user", parts=function_response_parts))

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=config,
            )

        # ── Extract text from final response ──
        # Try response.text first (can throw ValueError if no text parts)
        try:
            text = response.text
            if text:
                return text
        except (ValueError, AttributeError):
            pass

        # Fallback: iterate parts manually
        if response.candidates and response.candidates[0].content:
            text_parts = []
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text:
                    text_parts.append(part.text)
            if text_parts:
                return "\n".join(text_parts)

        # Debug: log what we got
        logger.warning(f"ZeRoN IA: Could not extract text. "
                      f"candidates={len(response.candidates) if response.candidates else 0}, "
                      f"finish_reason={getattr(response.candidates[0], 'finish_reason', 'N/A') if response.candidates else 'N/A'}")
        
        return "Lo siento, no pude procesar tu consulta en este momento. Intentá de nuevo."

    except Exception as e:
        logger.error(f"ZeRoN IA error: {e}", exc_info=True)
        return f"⚠️ Error al procesar tu consulta: {str(e)}"
