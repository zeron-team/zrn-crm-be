#!/usr/bin/env python3
"""
ZRN360° — Script de datos demo con trazabilidad completa.
Genera datos realistas de una software factory argentina.

Flujo de negocio:
  Lead → Contacto → Presupuesto → Cliente → Factura → Proyecto → Tickets
  Empleados → Fichadas → Liquidación de sueldos
  Proveedores → Servicios contratados → Pagos
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.models.client import Client
from app.models.contact import Contact
from app.models.lead import Lead
from app.models.product import Product
from app.models.provider import Provider
from app.models.provider_service import ProviderService
from app.models.client_service import ClientService
from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.quote import Quote
from app.models.quote_item import QuoteItem
from app.models.employee import Employee
from app.models.time_entry import TimeEntry
from app.models.calendar import CalendarEvent
from app.models.category import Family, Category, Subcategory
from app.models.payroll import PayrollConcept, PayrollPeriod, PayrollSlip, PayrollSlipItem
from app.models.project import Project, ProjectMember, ProjectVersion, Sprint, Task, TaskChecklistItem
from app.models.ticket import Ticket, TicketComment
from app.models.service_payment import ServicePayment
from app.models.note import Note
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"])
db = SessionLocal()
now = datetime.now(timezone.utc)
today = date.today()

def d(days_ago): return today - timedelta(days=days_ago)
def dt(days_ago, h=9, m=0): return datetime(today.year, today.month, today.day, h, m, tzinfo=timezone.utc) - timedelta(days=days_ago)

print("🌱 Generando datos demo ZRN360°...")

# ═══════════════════════════════════════════════
# 1. USUARIOS (equipo de la software factory)
# ═══════════════════════════════════════════════
print("  👤 Usuarios...")
users_data = [
    ("Martín García", "martin@zeron.ovh", "admin", Decimal("5.00")),
    ("Lucía Fernández", "lucia@zeron.ovh", "vendedor", Decimal("8.00")),
    ("Diego Rodríguez", "diego@zeron.ovh", "user", Decimal("0")),
    ("Camila López", "camila@zeron.ovh", "user", Decimal("0")),
    ("Santiago Morales", "santiago@zeron.ovh", "user", Decimal("0")),
]
users = []
for full_name, email, role, comm in users_data:
    u = db.query(User).filter(User.email == email).first()
    if not u:
        u = User(full_name=full_name, email=email, hashed_password=pwd_ctx.hash("Demo2026!"), role=role, is_active=True, commission_pct=comm)
        db.add(u)
        db.flush()
    users.append(u)
admin_user, vendedora, dev1, dev2, dev3 = users

# ═══════════════════════════════════════════════
# 2. CATEGORÍAS (Familias → Categorías → Subcategorías)
# ═══════════════════════════════════════════════
print("  📂 Categorías...")
families_data = {
    "Software": {"Desarrollo": ["Frontend", "Backend", "Mobile", "DevOps"], "Testing": ["QA Manual", "Automatización"]},
    "Infraestructura": {"Cloud": ["AWS", "GCP", "Azure"], "On-Premise": ["Servidores", "Networking"]},
    "Consultoría": {"Gestión": ["Project Management", "Scrum Master"], "Estrategia": ["Transformación Digital", "Auditoría IT"]},
}
for fam_name, cats in families_data.items():
    fam = Family(name=fam_name, code=fam_name[:3].upper(), description=f"Familia de {fam_name}")
    db.add(fam); db.flush()
    for cat_name, subs in cats.items():
        cat = Category(name=cat_name, code=cat_name[:3].upper(), family_id=fam.id)
        db.add(cat); db.flush()
        for sub in subs:
            db.add(Subcategory(name=sub, code=sub[:3].upper(), category_id=cat.id))

# ═══════════════════════════════════════════════
# 3. PRODUCTOS Y SERVICIOS (catálogo)
# ═══════════════════════════════════════════════
print("  🏷️  Productos y servicios...")
products_data = [
    ("Desarrollo Web Full Stack", "Desarrollo de aplicaciones web React + FastAPI", 850000, "ARS", "service", "Software", "Desarrollo", "Full Stack"),
    ("Desarrollo Mobile React Native", "App mobile multiplataforma iOS/Android", 950000, "ARS", "service", "Software", "Desarrollo", "Mobile"),
    ("Consultoría DevOps", "CI/CD, Docker, Kubernetes, monitoreo", 120, "USD", "service", "Infraestructura", "Cloud", "DevOps"),
    ("Soporte Técnico Mensual", "Mesa de ayuda, monitoreo 24/7, backups", 180000, "ARS", "service", "Infraestructura", "On-Premise", "Soporte"),
    ("Hosting VPS Premium", "4 vCPU, 8GB RAM, 100GB SSD, Ubuntu", 45, "USD", "service", "Infraestructura", "Cloud", "AWS"),
    ("Licencia Software CRM", "Licencia anual ZRN360 (hasta 50 usuarios)", 2500, "USD", "product", "Software", "Desarrollo", "CRM"),
    ("Hora de Desarrollo Senior", "Hora de desarrollo fullstack senior", 25000, "ARS", "manpower", "Software", "Desarrollo", "Full Stack"),
    ("Hora de Diseño UX/UI", "Hora de diseño de interfaces y experiencia", 22000, "ARS", "manpower", "Software", "Desarrollo", "Frontend"),
    ("Auditoría de Seguridad", "Penetration testing y reporte de vulnerabilidades", 3500, "USD", "service", "Consultoría", "Estrategia", "Auditoría IT"),
    ("Capacitación Equipo Scrum", "Workshop de 2 días Scrum + Kanban (hasta 15 personas)", 1200000, "ARS", "service", "Consultoría", "Gestión", "Scrum Master"),
    ("Dominio .com.ar", "Registro anual de dominio .com.ar", 15000, "ARS", "product", "Infraestructura", "Cloud", "DNS"),
    ("Certificado SSL Wildcard", "Certificado SSL wildcard anual", 120, "USD", "product", "Infraestructura", "Cloud", "SSL"),
]
products = []
for name, desc, price, cur, ptype, fam, cat, sub in products_data:
    p = Product(name=name, description=desc, price=Decimal(str(price)), currency=cur, type=ptype, family=fam, category=cat, subcategory=sub)
    db.add(p); db.flush(); products.append(p)

# ═══════════════════════════════════════════════
# 4. LEADS (prospectos en distintas etapas)
# ═══════════════════════════════════════════════
print("  🎯 Leads...")
leads_data = [
    ("Constructora del Sur SRL", "Ricardo Méndez", "rmendez@constructoradelsur.com.ar", "+54 11 4555-1234", "Qualified", "Referido", "Buenos Aires", "Necesitan sistema de gestión de obras y presupuestos"),
    ("Estudio Jurídico Paz & Asociados", "Dra. Valentina Paz", "vpaz@estudiopaz.com.ar", "+54 11 4777-5678", "Contacted", "LinkedIn", "CABA", "Consulta por digitalización de expedientes"),
    ("Farmacia Central SA", "Carlos Giménez", "cgimenez@farmaciacentral.com.ar", "+54 351 422-9012", "New", "Website", "Córdoba", "Interesados en sistema de stock y facturación electrónica"),
    ("Bodega Villa Andina", "Marcela Torres", "mtorres@villaandina.com.ar", "+54 261 420-3456", "Proposal", "Evento Tech", "Mendoza", "Necesitan e-commerce + integración MercadoLibre"),
    ("Logística Express SA", "Juan Pablo Herrera", "jpherrera@logisticaexpress.com.ar", "+54 11 4888-7890", "Lost", "Google Ads", "Buenos Aires", "Presupuesto fuera de rango. Recontactar en 6 meses"),
    ("Clínica San Martín", "Dr. Fernando Ríos", "frios@clinicasanmartin.com.ar", "+54 341 425-1122", "New", "Referido", "Rosario", "Sistema de turnos y historia clínica electrónica"),
]
leads = []
for i, (comp, contact, email, phone, status, source, city, notes) in enumerate(leads_data):
    l = Lead(company_name=comp, contact_name=contact, email=email, phone=phone, status=status, source=source, city=city, province=city, country="Argentina", notes=notes, created_at=dt(90-i*12))
    db.add(l); db.flush(); leads.append(l)
    # Contacto del lead
    db.add(Contact(name=contact, email=email, phone=phone, position="Decisor", lead_id=l.id))

# ═══════════════════════════════════════════════
# 5. CLIENTES (leads convertidos + existentes)
# ═══════════════════════════════════════════════
print("  🏢 Clientes...")
clients_data = [
    ("TechnoSoft Argentina SA", "TechnoSoft", "Responsable Inscripto", "30-71234567-8", "info@technosoft.com.ar", "+54 11 5555-0001", "Av. Corrientes 1234 P5", "CABA", "Buenos Aires", "Desarrollo de software"),
    ("Grupo Inmobiliario Altos SA", "Altos", "Responsable Inscripto", "30-71234568-6", "contacto@grupoaltos.com.ar", "+54 11 5555-0002", "Av. Libertador 5678", "CABA", "Buenos Aires", "Inmobiliaria y construcción"),
    ("Laboratorio Biosur SRL", "Biosur", "Responsable Inscripto", "30-71234569-4", "admin@biosur.com.ar", "+54 11 5555-0003", "Calle Pasteur 890", "Quilmes", "Buenos Aires", "Análisis clínicos"),
    ("Distribuidora Norte SA", "DisNorte", "Responsable Inscripto", "30-71234570-1", "ventas@disnorte.com.ar", "+54 381 555-0004", "Ruta 9 Km 1200", "San Miguel de Tucumán", "Tucumán", "Distribución mayorista"),
    ("Academia Digital Futuro", "ADF", "Monotributista", "20-35123456-7", "hola@academiadf.com.ar", "+54 11 5555-0005", "Av. Santa Fe 3456", "CABA", "Buenos Aires", "Educación online"),
    ("Exportadora Pampa SA", "Pampa Export", "Responsable Inscripto", "30-71234571-9", "comercio@pampexport.com.ar", "+54 11 5555-0006", "Puerto Madero Dique 3", "CABA", "Buenos Aires", "Exportación agropecuaria"),
]
clients = []
for name, trade, tax, cuit, email, phone, addr, city, prov, act in clients_data:
    c = Client(name=name, trade_name=trade, tax_condition=tax, cuit_dni=cuit, email=email, phone=phone, address=addr, city=city, province=prov, country="Argentina", activity=act, seller_id=vendedora.id)
    db.add(c); db.flush(); clients.append(c)

# Contactos de clientes
contacts_data = [
    ("Alejandro Ruiz", "aruiz@technosoft.com.ar", "+54 11 5555-1001", "CTO", 0),
    ("María Belén Costa", "mbcosta@technosoft.com.ar", "+54 11 5555-1002", "PM", 0),
    ("Fernando Iglesias", "figlesias@grupoaltos.com.ar", "+54 11 5555-2001", "Gerente IT", 1),
    ("Ana Moretti", "amoretti@grupoaltos.com.ar", "+54 11 5555-2002", "Directora Comercial", 1),
    ("Dr. Pablo Sánchez", "psanchez@biosur.com.ar", "+54 11 5555-3001", "Director", 2),
    ("Laura Méndez", "lmendez@biosur.com.ar", "+54 11 5555-3002", "Administración", 2),
    ("Roberto Acosta", "racosta@disnorte.com.ar", "+54 381 555-4001", "Gerente General", 3),
    ("Sofía Estrella", "sestrella@academiadf.com.ar", "+54 11 5555-5001", "Fundadora & CEO", 4),
    ("Martín Echeverría", "mecheverria@pampexport.com.ar", "+54 11 5555-6001", "Dir. Operaciones", 5),
]
for name, email, phone, pos, ci in contacts_data:
    db.add(Contact(name=name, email=email, phone=phone, position=pos, client_id=clients[ci].id))

# ═══════════════════════════════════════════════
# 6. PROVEEDORES Y SERVICIOS CONTRATADOS
# ═══════════════════════════════════════════════
print("  🤝 Proveedores...")
providers_data = [
    ("DigitalOcean LLC", "00-00000001-0", "billing@digitalocean.com", "+1 646-831-4500", "101 6th Ave, New York"),
    ("Amazon Web Services", "00-00000002-0", "aws-billing@amazon.com", "+1 206-266-1000", "410 Terry Ave, Seattle"),
    ("Google Cloud Platform", "00-00000003-0", "billing@google.com", "+1 650-253-0000", "1600 Amphitheatre Pkwy, Mountain View"),
    ("Telecom Argentina SA", "30-63945373-8", "empresas@telecom.com.ar", "+54 11 4968-3535", "Av. Alicia Moreau de Justo 50, CABA"),
    ("NIC Argentina", "30-66233255-1", "soporte@nic.ar", "+54 11 5300-4000", "Tucumán 744, CABA"),
]
providers = []
for name, cuit, email, phone, addr in providers_data:
    p = Provider(name=name, cuit_dni=cuit, email=email, phone=phone, address=addr)
    db.add(p); db.flush(); providers.append(p)
    db.add(Contact(name=f"Soporte {name}", email=email, phone=phone, position="Account Manager", provider_id=p.id))

# Servicios contratados a proveedores
prov_services_data = [
    (0, "VPS Production 8GB", 48.00, "USD", "Monthly", d(10)),
    (0, "VPS Staging 4GB", 24.00, "USD", "Monthly", d(40)),
    (1, "AWS S3 Storage", 35.00, "USD", "Monthly", d(10)),
    (1, "AWS Route53 DNS", 5.00, "USD", "Monthly", d(10)),
    (2, "Google Workspace Business", 156.00, "USD", "Monthly", d(10)),
    (3, "Fibra Óptica 300Mbps", 45000.00, "ARS", "Monthly", d(60)),
    (4, "Dominio zeron.ovh", 8500.00, "ARS", "Yearly", d(200)),
]
prov_svcs = []
for pi, name, cost, cur, cycle, exp in prov_services_data:
    ps = ProviderService(provider_id=providers[pi].id, name=name, cost_price=Decimal(str(cost)), currency=cur, billing_cycle=cycle, expiration_date=exp)
    db.add(ps); db.flush(); prov_svcs.append(ps)

# ═══════════════════════════════════════════════
# 7. SERVICIOS A CLIENTES (contratos activos)
# ═══════════════════════════════════════════════
print("  📋 Servicios a clientes...")
client_svcs_data = [
    (0, 3, "Soporte Técnico Mensual", "Active", "ARS", "Monthly", d(180)),
    (0, 4, "Hosting VPS Premium", "Active", "USD", "Monthly", d(180)),
    (1, 3, "Soporte Técnico Mensual", "Active", "ARS", "Monthly", d(120)),
    (2, 3, "Soporte Técnico Mensual", "Active", "ARS", "Monthly", d(90)),
    (2, 4, "Hosting VPS Premium", "Active", "USD", "Monthly", d(90)),
    (4, 4, "Hosting VPS Premium", "Active", "USD", "Monthly", d(60)),
    (5, 5, "Licencia CRM Anual", "Active", "USD", "Yearly", d(30)),
]
for ci, pi, name, status, cur, cycle, start in client_svcs_data:
    db.add(ClientService(client_id=clients[ci].id, product_id=products[pi].id, name=name, status=status, currency=cur, billing_cycle=cycle, start_date=start))

# ═══════════════════════════════════════════════
# 8. INVOICE STATUSES
# ═══════════════════════════════════════════════
print("  📊 Estados de facturas...")
statuses_data = [
    ("Pendiente", "Factura emitida, pendiente de cobro", "#F59E0B"),
    ("Cobrada", "Factura cobrada en su totalidad", "#10B981"),
    ("Vencida", "Factura vencida sin cobrar", "#EF4444"),
    ("Parcial", "Cobro parcial recibido", "#3B82F6"),
    ("Anulada", "Factura anulada", "#6B7280"),
]
inv_statuses = []
for name, desc, color in statuses_data:
    s = db.query(InvoiceStatus).filter(InvoiceStatus.name == name).first()
    if not s:
        s = InvoiceStatus(name=name, description=desc, color_code=color)
        db.add(s); db.flush()
    inv_statuses.append(s)

# ═══════════════════════════════════════════════
# 9. PRESUPUESTOS CON ITEMS (trazabilidad lead→quote→client)
# ═══════════════════════════════════════════════
print("  📝 Presupuestos...")
quotes_data = [
    # (quote_number, client_idx|None, lead_idx|None, days_ago, expiry_offset, status, currency, items[(prod_idx, qty, unit_price)])
    ("QT-20260101", 0, None, 60, 30, "Accepted", "ARS", [(0, 1, 850000), (6, 40, 25000)]),
    ("QT-20260102", 1, None, 45, 30, "Accepted", "ARS", [(0, 1, 850000), (7, 20, 22000)]),
    ("QT-20260103", 2, None, 30, 30, "Sent", "ARS", [(3, 12, 180000), (4, 1, 45*1100)]),
    ("QT-20260104", None, 0, 20, 30, "Draft", "ARS", [(0, 1, 950000), (9, 1, 1200000)]),
    ("QT-20260105", None, 3, 15, 30, "Sent", "USD", [(1, 1, 950000), (2, 20, 120)]),
    ("QT-20260106", 4, None, 10, 30, "Accepted", "ARS", [(5, 1, 2500*1100), (4, 1, 45*1100)]),
    ("QT-20260107", 5, None, 5, 30, "Draft", "USD", [(8, 1, 3500), (2, 10, 120)]),
]
quotes = []
for qnum, ci, li, days, exp_off, status, cur, items_list in quotes_data:
    subtotal = sum(qty * up for _, qty, up in items_list)
    tax = round(subtotal * Decimal("0.21"), 2)
    total = subtotal + tax
    q = Quote(quote_number=qnum, client_id=clients[ci].id if ci is not None else None, lead_id=leads[li].id if li is not None else None,
              issue_date=d(days), expiry_date=d(days - exp_off), status=status, currency=cur,
              subtotal=Decimal(str(subtotal)), tax_amount=Decimal(str(tax)), total_amount=Decimal(str(total)),
              seller_id=vendedora.id, commission_pct=Decimal("8.00"),
              notes=f"Presupuesto generado para demo - {status}")
    db.add(q); db.flush(); quotes.append(q)
    for prod_idx, qty, up in items_list:
        db.add(QuoteItem(quote_id=q.id, product_id=products[prod_idx].id, description=products[prod_idx].name,
                         quantity=Decimal(str(qty)), unit_price=Decimal(str(up)), total_price=Decimal(str(qty*up))))

# ═══════════════════════════════════════════════
# 10. FACTURAS CON ITEMS (trazadas a clientes y quotes)
# ═══════════════════════════════════════════════
print("  🧾 Facturas...")
invoices_data = [
    # Emitidas (type=created) - trazadas a quotes aceptados
    ("FA-A-00001-00000001", 1850000, "ARS", "created", 55, 25, None, 0, 0, 1, [(0, 1, 850000), (6, 40, 25000)]),
    ("FA-A-00001-00000002", 1290000, "ARS", "created", 40, 10, None, 1, 1, 1, [(0, 1, 850000), (7, 20, 22000)]),
    ("FA-A-00001-00000003", 180000, "ARS", "created", 28, -2, None, 0, None, 0, [(3, 1, 180000)]),
    ("FA-A-00001-00000004", 180000, "ARS", "created", 0, 30, None, 2, None, 0, [(3, 1, 180000)]),
    ("FA-B-00001-00000001", 2799500, "ARS", "created", 8, 38, None, 4, 5, 0, [(5, 1, 2750000), (4, 1, 49500)]),
    ("FA-A-00001-00000005", 180000, "ARS", "created", 14, 16, None, 1, None, 0, [(3, 1, 180000)]),
    # Recibidas (type=received) - de proveedores
    ("PROV-DO-2026-001", 48, "USD", "received", 30, 0, 0, None, None, 1, []),
    ("PROV-DO-2026-002", 24, "USD", "received", 30, 0, 0, None, None, 1, []),
    ("PROV-AWS-2026-001", 40, "USD", "received", 28, -2, 1, None, None, 2, []),
    ("PROV-TEL-2026-001", 45000, "ARS", "received", 25, 5, 3, None, None, 1, []),
]
invoices = []
for inv_num, amount, cur, itype, days_ago, due_off, prov_i, cli_i, q_i, stat_i, items_list in invoices_data:
    inv = Invoice(
        invoice_number=inv_num, amount=Decimal(str(amount)), currency=cur, type=itype,
        issue_date=dt(days_ago), due_date=dt(days_ago - due_off),
        client_id=clients[cli_i].id if cli_i is not None else None,
        provider_id=providers[prov_i].id if prov_i is not None else None,
        quote_id=quotes[q_i].id if q_i is not None else None,
        status_id=inv_statuses[stat_i].id, seller_id=vendedora.id,
        imp_neto=Decimal(str(round(amount / 1.21, 2))), imp_iva=Decimal(str(round(amount - amount / 1.21, 2))),
        notes=f"Factura demo - {'Emitida' if itype == 'created' else 'Recibida'}"
    )
    db.add(inv); db.flush(); invoices.append(inv)
    for prod_idx, qty, up in items_list:
        db.add(InvoiceItem(invoice_id=inv.id, product_id=products[prod_idx].id, description=products[prod_idx].name,
                           quantity=Decimal(str(qty)), unit_price=Decimal(str(up)), total_price=Decimal(str(qty*up))))

# ═══════════════════════════════════════════════
# 11. EMPLEADOS
# ═══════════════════════════════════════════════
print("  👷 Empleados...")
employees_data = [
    ("001", "Martín", "García", "30123456", "20-30123456-7", d(1800), "IT", "Director de Tecnología", "permanent", 1500000, admin_user.id),
    ("002", "Lucía", "Fernández", "31234567", "27-31234567-8", d(1200), "Ventas", "Ejecutiva Comercial", "permanent", 1100000, vendedora.id),
    ("003", "Diego", "Rodríguez", "32345678", "20-32345678-9", d(900), "IT", "Desarrollador Senior", "permanent", 1300000, dev1.id),
    ("004", "Camila", "López", "33456789", "27-33456789-0", d(600), "IT", "Desarrolladora Full Stack", "permanent", 1200000, dev2.id),
    ("005", "Santiago", "Morales", "34567890", "20-34567890-1", d(300), "IT", "Desarrollador Junior", "permanent", 850000, dev3.id),
    ("006", "Valentina", "Pérez", "35678901", "27-35678901-2", d(400), "Administración", "Contadora", "permanent", 1000000, None),
    ("007", "Tomás", "Acuña", "36789012", "20-36789012-3", d(150), "IT", "DevOps Engineer", "permanent", 1350000, None),
    ("008", "Florencia", "Martínez", "37890123", "27-37890123-4", d(90), "RRHH", "Analista de RRHH", "permanent", 900000, None),
]
employees = []
for leg, fn, ln, dni, cuil, hire, dept, pos, ct, sal, uid in employees_data:
    e = Employee(legajo=leg, first_name=fn, last_name=ln, dni=dni, cuil=cuil, hire_date=hire, department=dept, position=pos,
                 contract_type=ct, salary=Decimal(str(sal)), salary_currency="ARS", user_id=uid, is_active=True,
                 email=f"{fn.lower()}.{ln.lower()}@zeron.ovh", phone=f"+54 11 5555-{leg}1",
                 address="Av. Demo 1234", city="CABA", province="Buenos Aires", bank_name="Banco Galicia", bank_cbu=f"007005550000{dni}01")
    db.add(e); db.flush(); employees.append(e)
employees[0].supervisor_id = None  # Director no tiene supervisor
for emp in employees[1:]:
    emp.supervisor_id = employees[0].id  # Todos reportan al director

# ═══════════════════════════════════════════════
# 12. FICHADAS (TIME ENTRIES) - últimos 5 días
# ═══════════════════════════════════════════════
print("  ⏰ Fichadas...")
for day_offset in range(5):
    for emp in employees:
        for etype, h, m in [("check_in", 9, 0), ("break_start", 13, 0), ("break_end", 14, 0), ("check_out", 18, 0)]:
            db.add(TimeEntry(employee_id=emp.id, entry_type=etype, timestamp=dt(day_offset, h, m), ip_address="192.168.1.100"))

# ═══════════════════════════════════════════════
# 13. LIQUIDACIÓN DE SUELDOS
# ═══════════════════════════════════════════════
print("  💰 Liquidación de sueldos...")
concepts_data = [
    ("BASICO", "Sueldo Básico", "remunerativo", "otro", "fijo", None, "employee", True, 1),
    ("PREST", "Presentismo", "remunerativo", "otro", "porcentaje", Decimal("8.33"), "employee", True, 2),
    ("JUB", "Jubilación", "deduccion", "jubilacion", "porcentaje", Decimal("11.00"), "employee", True, 10),
    ("OS", "Obra Social", "deduccion", "obra_social", "porcentaje", Decimal("3.00"), "employee", True, 11),
    ("PAMI", "Ley 19.032 (PAMI)", "deduccion", "pami", "porcentaje", Decimal("3.00"), "employee", True, 12),
    ("SIND", "Sindicato", "deduccion", "sindicato", "porcentaje", Decimal("2.00"), "employee", True, 13),
    ("JUB_E", "Contrib. Jubilación Empleador", "deduccion", "jubilacion", "porcentaje", Decimal("18.00"), "employer", True, 20),
]
concepts = []
for code, name, ctype, cat, calc, rate, applies, mandatory, sort in concepts_data:
    c = PayrollConcept(code=code, name=name, type=ctype, category=cat, calc_mode=calc, default_rate=rate, applies_to=applies, is_mandatory=mandatory, sort_order=sort)
    db.add(c); db.flush(); concepts.append(c)

# Periodo Feb 2026
period = PayrollPeriod(year=2026, month=2, description="Febrero 2026", period_type="monthly", status="confirmed")
db.add(period); db.flush()

for emp in employees:
    gross = emp.salary
    present = round(gross * Decimal("0.0833"), 2)
    total_rem = gross + present
    jub = round(total_rem * Decimal("0.11"), 2)
    os_ded = round(total_rem * Decimal("0.03"), 2)
    pami = round(total_rem * Decimal("0.03"), 2)
    sind = round(total_rem * Decimal("0.02"), 2)
    total_ded = jub + os_ded + pami + sind
    net = total_rem - total_ded
    employer_cost = round(total_rem * Decimal("0.18"), 2)

    slip = PayrollSlip(period_id=period.id, employee_id=emp.id, gross_salary=gross,
                       total_remunerativo=total_rem, total_no_remunerativo=0, total_deductions=total_ded,
                       net_salary=net, total_employer_cost=employer_cost, status="confirmed")
    db.add(slip); db.flush()
    items = [
        (concepts[0], "remunerativo", None, None, gross, 1),
        (concepts[1], "remunerativo", Decimal("8.33"), gross, present, 2),
        (concepts[2], "deduccion", Decimal("11.00"), total_rem, jub, 10),
        (concepts[3], "deduccion", Decimal("3.00"), total_rem, os_ded, 11),
        (concepts[4], "deduccion", Decimal("3.00"), total_rem, pami, 12),
        (concepts[5], "deduccion", Decimal("2.00"), total_rem, sind, 13),
    ]
    for concept, itype, rate, base, amount, sort in items:
        db.add(PayrollSlipItem(slip_id=slip.id, concept_id=concept.id, concept_code=concept.code, concept_name=concept.name,
                               type=itype, rate=rate, base_amount=base, amount=amount, sort_order=sort))

# ═══════════════════════════════════════════════
# 14. PROYECTOS CON SPRINTS, TASKS Y CHECKLISTS
# ═══════════════════════════════════════════════
print("  📁 Proyectos y tareas...")
proj1 = Project(name="ZRN360 CRM", description="Sistema CRM integral para Zeron", key="ZRN", status="active", methodology="scrum", client_id=clients[0].id, quote_id=quotes[0].id, created_by=admin_user.id)
db.add(proj1); db.flush()
for u in users:
    db.add(ProjectMember(project_id=proj1.id, user_id=u.id, role="owner" if u == admin_user else "member"))

v1 = ProjectVersion(project_id=proj1.id, name="v3.0.0", description="Versión con módulos RRHH, Proyectos y Tickets", start_date=d(90), status="in_progress")
db.add(v1); db.flush()

sprint1 = Sprint(project_id=proj1.id, version_id=v1.id, name="Sprint 12 - RRHH", goal="Completar módulos de empleados, fichadas y liquidación", start_date=d(14), end_date=d(0), status="active")
db.add(sprint1); db.flush()

tasks_data = [
    ("ZRN-45", "Módulo de Empleados", "epic", "done", "high", dev1.id, 13, [(True, "CRUD empleados"), (True, "Ficha detallada"), (True, "Jerarquía de supervisores")]),
    ("ZRN-46", "Sistema de Fichadas", "feature", "done", "high", dev2.id, 8, [(True, "Check-in/out"), (True, "Pausas y descansos"), (True, "IP logging")]),
    ("ZRN-47", "Liquidación de Sueldos", "feature", "in_review", "critical", dev1.id, 13, [(True, "Conceptos de liquidación"), (True, "Recibos de sueldo"), (False, "Exportar PDF recibo")]),
    ("ZRN-48", "Integración ARCA/AFIP", "feature", "in_progress", "high", dev2.id, 8, [(True, "Factura A"), (True, "Factura B"), (False, "Nota de Crédito"), (False, "Nota de Débito")]),
    ("ZRN-49", "Dashboard BI avanzado", "story", "todo", "medium", dev3.id, 5, [(False, "Gráficos de rentabilidad"), (False, "KPIs por vendedor"), (False, "Filtros por período")]),
    ("ZRN-50", "Fix: Cálculo IVA en facturas multi-moneda", "bug", "done", "critical", dev1.id, 3, [(True, "Identificar bug"), (True, "Fix exchange rate"), (True, "Test regresión")]),
]
for key, title, ttype, status, prio, assigned, sp, checklist in tasks_data:
    t = Task(project_id=proj1.id, sprint_id=sprint1.id, key=key, title=title, type=ttype, status=status, priority=prio,
             assigned_to=assigned, reporter=admin_user.id, story_points=sp, due_date=d(0))
    db.add(t); db.flush()
    for i, (checked, text) in enumerate(checklist):
        db.add(TaskChecklistItem(task_id=t.id, text=text, is_checked=checked, position=i))

# Proyecto 2
proj2 = Project(name="Portal Inmobiliario Altos", description="Plataforma web de propiedades para Grupo Altos", key="ALT", status="active", methodology="kanban", client_id=clients[1].id, quote_id=quotes[1].id, created_by=admin_user.id)
db.add(proj2); db.flush()
db.add(ProjectMember(project_id=proj2.id, user_id=admin_user.id, role="owner"))
db.add(ProjectMember(project_id=proj2.id, user_id=dev2.id, role="member"))
t2 = Task(project_id=proj2.id, key="ALT-1", title="Diseño UI/UX del portal", type="task", status="in_progress", priority="high", assigned_to=dev2.id, reporter=admin_user.id, story_points=8)
db.add(t2); db.flush()

# ═══════════════════════════════════════════════
# 15. TICKETS DE SOPORTE
# ═══════════════════════════════════════════════
print("  🎫 Tickets...")
tickets_data = [
    ("TK-0001", "Error al generar PDF de factura", "Al intentar exportar factura FA-A-00001-00000003 a PDF, da error 500 en el backend.", "resolved", "high", "technical", 0, dev1.id),
    ("TK-0002", "Solicitud: Agregar campo CUIT en reporte Excel", "Necesitamos que el export a Excel de clientes incluya el CUIT.", "closed", "medium", "general", 0, dev2.id),
    ("TK-0003", "Dashboard no muestra facturas del mes", "Los widgets de ingresos muestran $0 para marzo 2026.", "in_progress", "critical", "technical", 1, dev1.id),
    ("TK-0004", "Consulta sobre integración API", "¿Se puede integrar ZRN360 con nuestro sistema SAP?", "open", "low", "general", 5, None),
    ("TK-0005", "Lentitud al cargar lista de productos", "La página de productos tarda +5 segundos en cargar con 200+ productos.", "waiting", "medium", "technical", 2, dev3.id),
]
for tnum, subj, desc, status, prio, cat, ci, assigned in tickets_data:
    tk = Ticket(ticket_number=tnum, subject=subj, description=desc, status=status, priority=prio, category=cat,
                client_id=clients[ci].id, assigned_to=assigned, created_by=admin_user.id)
    db.add(tk); db.flush()
    db.add(TicketComment(ticket_id=tk.id, user_id=admin_user.id, content=f"Ticket creado. {desc}", comment_type="comment"))
    if status in ("resolved", "closed"):
        db.add(TicketComment(ticket_id=tk.id, user_id=assigned, content="Resuelto. Se aplicó el fix en producción.", comment_type="comment"))

# ═══════════════════════════════════════════════
# 16. CALENDARIO (eventos próximos y pasados)
# ═══════════════════════════════════════════════
print("  📅 Calendario...")
events_data = [
    ("Reunión kickoff - Portal Altos", "Definición de alcance y milestones con el cliente", dt(2, 10), dt(2, 11, 30), "Meeting", "#3788d8", 1, "completed"),
    ("Demo Sprint 11 - ZRN360", "Presentación de avances módulos RRHH", dt(0, 15), dt(0, 16), "Meeting", "#10B981", 0, "completed"),
    ("Vencimiento factura FA-A-00001-00000003", "Cobro pendiente Laboratorio Biosur", dt(-2, 9), dt(-2, 9, 30), "Billing", "#EF4444", 2, "pending"),
    ("Capacitación Scrum - Academia DF", "Workshop de 2 días para equipo ADF", dt(-5, 9), dt(-4, 18), "Service Expiration", "#8B5CF6", 4, "pending"),
    ("Renovación hosting DigitalOcean", "Renovar VPS de producción y staging", dt(-10, 9), dt(-10, 10), "Service Expiration", "#F59E0B", None, "pending"),
    ("Llamada seguimiento lead Constructora del Sur", "Recontactar para cerrar presupuesto QT-20260104", dt(-3, 11), dt(-3, 11, 30), "Meeting", "#3788d8", None, "pending"),
    ("Entrega v3.0.0 ZRN360", "Release de versión con RRHH, Proyectos y Tickets", dt(-15, 9), dt(-15, 18), "Other", "#10B981", 0, "pending"),
]
for title, desc, start, end, rel, color, ci, status in events_data:
    db.add(CalendarEvent(title=title, description=desc, start_date=start, end_date=end, related_to=rel, color=color,
                         client_id=clients[ci].id if ci is not None else None, status=status))

# ═══════════════════════════════════════════════
# 17. PAGOS DE SERVICIOS A PROVEEDORES
# ═══════════════════════════════════════════════
print("  💳 Pagos de servicios...")
for month in [1, 2]:
    for ps in prov_svcs[:5]:  # Solo los de USD
        rate = Decimal("1100.50") if month == 1 else Decimal("1120.75")
        db.add(ServicePayment(provider_service_id=ps.id, period_month=month, period_year=2026,
                              amount=ps.cost_price, currency=ps.currency, exchange_rate=rate,
                              amount_ars=round(ps.cost_price * rate, 2), payment_date=datetime(2026, month, 5, tzinfo=timezone.utc)))

# ═══════════════════════════════════════════════
# 18. NOTAS ADHESIVAS (sticky notes)
# ═══════════════════════════════════════════════
print("  📌 Notas...")
notes_data = [
    ("Revisar contrato", "Verificar cláusula de penalidad por demora en entrega", "yellow", "client", clients[0].id),
    ("Pedir certificado ARCA", "Solicitar certificado digital .crt y .key para facturación electrónica", "blue", "client", clients[5].id),
    ("Presupuesto pendiente", "Enviar presupuesto revisado a Constructora del Sur antes del viernes", "pink", "lead", leads[0].id),
    ("Bug crítico dashboard", "El widget de ingresos no filtra por moneda - investigar", "orange", "ticket", None),
]
for title, content, color, etype, eid in notes_data:
    db.add(Note(title=title, content=content, color=color, entity_type=etype, entity_id=eid, created_by=admin_user.id))

# ═══════════════════════════════════════════════
# COMMIT FINAL
# ═══════════════════════════════════════════════
db.commit()
db.close()

print("\n✅ ¡Datos demo generados exitosamente!")
print("=" * 50)
print(f"  👤 {len(users_data)} usuarios")
print(f"  📂 {len(families_data)} familias, categorías y subcategorías")
print(f"  🏷️  {len(products)} productos/servicios")
print(f"  🎯 {len(leads)} leads")
print(f"  🏢 {len(clients)} clientes + {len(contacts_data)} contactos")
print(f"  🤝 {len(providers)} proveedores + {len(prov_svcs)} servicios contratados")
print(f"  📋 {len(client_svcs_data)} servicios a clientes")
print(f"  📝 {len(quotes)} presupuestos con items")
print(f"  🧾 {len(invoices)} facturas con items")
print(f"  👷 {len(employees)} empleados")
print(f"  ⏰ {len(employees) * 5 * 4} fichadas (5 días)")
print(f"  💰 1 período de liquidación con {len(employees)} recibos")
print(f"  📁 2 proyectos, 1 sprint, {len(tasks_data)+1} tareas")
print(f"  🎫 {len(tickets_data)} tickets de soporte")
print(f"  📅 {len(events_data)} eventos de calendario")
print(f"  💳 {5 * 2} pagos de servicios")
print(f"  📌 {len(notes_data)} notas")
print("=" * 50)
print("  🔑 Login: admin@zeron.ovh / Admin123!")
print("  🔑 Login: lucia@zeron.ovh / Demo2026!")
print("  🔑 Login: diego@zeron.ovh / Demo2026!")
