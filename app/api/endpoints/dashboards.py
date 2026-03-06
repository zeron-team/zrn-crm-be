from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, func as sqlfunc
from app.database import get_db
from app.models.invoice import Invoice
from app.models.product import Product
from app.models.client import Client
from app.models.provider import Provider
from app.models.purchase_order import PurchaseOrder
from app.models.payment_order import PaymentOrder
from app.models.delivery_note import DeliveryNote
from app.models.inventory import InventoryItem
from app.models.warehouse import Warehouse
from app.models.quote import Quote
from app.models.contact import Contact
from app.models.provider_service import ProviderService
from datetime import datetime, timedelta, date as date_type

def safe_month(d):
    """Safely get month from date or datetime"""
    if d is None: return None
    if hasattr(d, 'month'): return d.month
    return None

def safe_year(d):
    """Safely get year from date or datetime"""
    if d is None: return None
    if hasattr(d, 'year'): return d.year
    return None

def to_datetime(d):
    """Convert date or datetime to datetime for comparison"""
    if d is None: return None
    if isinstance(d, datetime): return d
    if isinstance(d, date_type): return datetime.combine(d, datetime.min.time())
    return None

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

def inv_ars(i):
    """Get ARS-equivalent amount for an invoice."""
    if i.amount_ars:
        return float(i.amount_ars)
    if i.currency == 'ARS':
        return float(i.amount or 0)
    rate = float(i.exchange_rate or i.mon_cotiz or 1)
    return float(i.amount or 0) * rate

def pay_ars(p):
    """Get ARS-equivalent amount for a service payment."""
    if p.amount_ars:
        return float(p.amount_ars)
    if hasattr(p, 'currency') and p.currency == 'ARS':
        return float(p.amount or 0)
    rate = float(p.exchange_rate or 1)
    return float(p.amount or 0) * rate

def get_latest_usd_rate(db):
    """Get latest USD sell rate from exchange_rates table."""
    from app.models.exchange_rate import ExchangeRate
    rate = db.query(ExchangeRate).filter(
        ExchangeRate.currency == 'USD'
    ).order_by(ExchangeRate.date.desc()).first()
    return float(rate.sell_rate) if rate else 1.0

def svc_cost_ars(service, usd_rate):
    """Convert a provider service cost_price to ARS."""
    cost = float(service.cost_price or 0)
    if service.currency == 'ARS':
        return cost
    return cost * usd_rate

# ─── SALES DASHBOARD ───
@router.get("/sales")
def sales_dashboard(db: Session = Depends(get_db)):
    invoices = db.query(Invoice).all()
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    total_invoiced = sum(inv_ars(i) for i in invoices)
    this_month = sum(inv_ars(i) for i in invoices if safe_month(i.issue_date) == current_month and safe_year(i.issue_date) == current_year)
    last_month_dt = now.replace(day=1) - timedelta(days=1)
    last_month = sum(inv_ars(i) for i in invoices if safe_month(i.issue_date) == last_month_dt.month and safe_year(i.issue_date) == last_month_dt.year)
    growth = round(((this_month - last_month) / last_month * 100) if last_month > 0 else 0, 1)

    paid_invoices = [i for i in invoices if i.status_id and i.status_id == 3]
    pending_invoices = [i for i in invoices if i.status_id and i.status_id in [1, 2, 4, 8]]
    overdue_invoices = [i for i in invoices if i.due_date and to_datetime(i.due_date) < now and i.status_id in [1, 2]]

    # Monthly breakdown (last 12 months)
    monthly = []
    for m in range(11, -1, -1):
        dt = now - timedelta(days=30 * m)
        month_invs = [i for i in invoices if safe_month(i.issue_date) == dt.month and safe_year(i.issue_date) == dt.year]
        month_total = sum(inv_ars(i) for i in month_invs)
        monthly.append({"month": dt.strftime("%b %Y"), "total": round(month_total, 2), "count": len(month_invs)})

    # By client (using ARS amounts)
    client_sales = {}
    for i in invoices:
        cid = i.client_id or 0
        if cid not in client_sales:
            client_sales[cid] = {"amount": 0, "count": 0}
        client_sales[cid]["amount"] += inv_ars(i)
        client_sales[cid]["count"] += 1

    top_clients = []
    for cid, data in sorted(client_sales.items(), key=lambda x: x[1]["amount"], reverse=True)[:10]:
        client = db.query(Client).filter(Client.id == cid).first() if cid else None
        top_clients.append({"client_id": cid, "client_name": client.name if client else "Sin cliente", "amount": round(data["amount"], 2), "count": data["count"]})

    # By type
    type_breakdown = {}
    for i in invoices:
        t = i.type or "Factura"
        if t not in type_breakdown:
            type_breakdown[t] = {"amount": 0, "count": 0}
        type_breakdown[t]["amount"] += inv_ars(i)
        type_breakdown[t]["count"] += 1

    # By currency (show original amounts per currency for reference)
    currency_breakdown = {}
    for i in invoices:
        c = i.currency or "ARS"
        if c not in currency_breakdown:
            currency_breakdown[c] = {"amount": 0, "amount_ars": 0, "count": 0}
        currency_breakdown[c]["amount"] += float(i.amount or 0)
        currency_breakdown[c]["amount_ars"] += inv_ars(i)
        currency_breakdown[c]["count"] += 1

    # ── Commission data from quotes ──
    quotes = db.query(Quote).all()
    from app.models.user import User
    sellers = db.query(User).filter(User.role == "vendedor").all()
    usd_rate = get_latest_usd_rate(db)

    total_commissions = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in quotes if q.commission_pct)
    accepted_commissions = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in quotes if q.commission_pct and q.status == "Accepted")

    # Per-seller commission summary
    seller_commissions = []
    for s in sellers:
        sq = [q for q in quotes if q.seller_id == s.id]
        total_c = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in sq if q.commission_pct)
        won_c = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in sq if q.commission_pct and q.status == "Accepted")
        seller_commissions.append({"seller_id": s.id, "seller_name": s.full_name, "total_commission": round(total_c, 2), "won_commission": round(won_c, 2), "quotes_count": len(sq)})

    return {
        "total_invoiced": round(total_invoiced, 2),
        "this_month": round(this_month, 2),
        "last_month": round(last_month, 2),
        "growth_pct": growth,
        "total_count": len(invoices),
        "paid_count": len(paid_invoices),
        "paid_amount": round(sum(inv_ars(i) for i in paid_invoices), 2),
        "pending_count": len(pending_invoices),
        "pending_amount": round(sum(inv_ars(i) for i in pending_invoices), 2),
        "overdue_count": len(overdue_invoices),
        "overdue_amount": round(sum(inv_ars(i) for i in overdue_invoices), 2),
        "avg_invoice": round(total_invoiced / len(invoices) if invoices else 0, 2),
        "monthly": monthly,
        "top_clients": top_clients,
        "type_breakdown": [{"type": k, **v} for k, v in type_breakdown.items()],
        "currency_breakdown": [{"currency": k, **v} for k, v in currency_breakdown.items()],
        "total_commissions": round(total_commissions, 2),
        "accepted_commissions": round(accepted_commissions, 2),
        "seller_commissions": seller_commissions,
        "latest_usd_rate": usd_rate,
    }

# ─── PURCHASES DASHBOARD ───
@router.get("/purchases")
def purchases_dashboard(db: Session = Depends(get_db)):
    pos = db.query(PurchaseOrder).all()
    pays = db.query(PaymentOrder).all()

    total_po = sum(float(p.total_amount or 0) for p in pos)
    total_pay = sum(float(p.amount or 0) for p in pays)

    po_by_status = {}
    for p in pos:
        s = p.status or "pendiente"
        po_by_status.setdefault(s, {"count": 0, "amount": 0})
        po_by_status[s]["count"] += 1
        po_by_status[s]["amount"] += float(p.total_amount or 0)

    pay_by_status = {}
    for p in pays:
        s = p.status or "pendiente"
        pay_by_status.setdefault(s, {"count": 0, "amount": 0})
        pay_by_status[s]["count"] += 1
        pay_by_status[s]["amount"] += float(p.amount or 0)

    # By provider
    provider_spend = {}
    for p in pos:
        pid = p.provider_id or 0
        provider_spend.setdefault(pid, {"po_amount": 0, "po_count": 0})
        provider_spend[pid]["po_amount"] += float(p.total_amount or 0)
        provider_spend[pid]["po_count"] += 1
    for p in pays:
        pid = p.provider_id or 0
        provider_spend.setdefault(pid, {"po_amount": 0, "po_count": 0})
        provider_spend[pid].setdefault("pay_amount", 0)
        provider_spend[pid].setdefault("pay_count", 0)
        provider_spend[pid]["pay_amount"] += float(p.amount or 0)
        provider_spend[pid]["pay_count"] += 1

    top_providers = []
    for pid, data in sorted(provider_spend.items(), key=lambda x: x[1].get("po_amount", 0), reverse=True)[:10]:
        prov = db.query(Provider).filter(Provider.id == pid).first() if pid else None
        top_providers.append({"provider_id": pid, "provider_name": prov.name if prov else "Sin proveedor", **data})

    # Monthly
    now = datetime.now()
    po_monthly = []
    for m in range(11, -1, -1):
        dt = now - timedelta(days=30 * m)
        month_total = sum(float(p.total_amount or 0) for p in pos if safe_month(p.date) == dt.month and safe_year(p.date) == dt.year)
        po_monthly.append({"month": dt.strftime("%b %Y"), "total": round(month_total, 2)})

    return {
        "total_purchase_orders": len(pos),
        "total_po_amount": round(total_po, 2),
        "total_payment_orders": len(pays),
        "total_pay_amount": round(total_pay, 2),
        "po_by_status": [{"status": k, **v} for k, v in po_by_status.items()],
        "pay_by_status": [{"status": k, **v} for k, v in pay_by_status.items()],
        "top_providers": top_providers,
        "po_monthly": po_monthly,
    }

# ─── INVENTORY DASHBOARD ───
@router.get("/inventory")
def inventory_dashboard(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).all()
    warehouses = db.query(Warehouse).all()
    products = {p.id: p for p in db.query(Product).all()}

    total_items = len(items)
    total_stock = sum(float(i.stock or 0) for i in items)
    total_value = 0
    critical = []
    over = []
    by_warehouse = {}
    by_category = {}
    by_type = {}

    for i in items:
        p = products.get(i.product_id)
        price = float(p.price or 0) if p else 0
        stock = float(i.stock or 0)
        val = price * stock
        total_value += val

        # Status
        min_s = float(i.min_stock or 0)
        max_s = float(i.max_stock or 0)
        if min_s > 0 and stock <= min_s:
            critical.append({"product": p.name if p else "?", "stock": stock, "min_stock": min_s, "unit": i.unit})
        if max_s > 0 and stock >= max_s:
            over.append({"product": p.name if p else "?", "stock": stock, "max_stock": max_s, "unit": i.unit})

        # By warehouse
        wid = i.warehouse_id or 0
        by_warehouse.setdefault(wid, {"count": 0, "value": 0, "stock": 0})
        by_warehouse[wid]["count"] += 1
        by_warehouse[wid]["value"] += val
        by_warehouse[wid]["stock"] += stock

        # By category
        cat = p.category if p else "Sin categoría"
        by_category.setdefault(cat, {"count": 0, "value": 0})
        by_category[cat]["count"] += 1
        by_category[cat]["value"] += val

        # By type
        typ = p.type if p else "unknown"
        by_type.setdefault(typ, {"count": 0, "stock": 0, "value": 0})
        by_type[typ]["count"] += 1
        by_type[typ]["stock"] += stock
        by_type[typ]["value"] += val

    wh_map = {w.id: w.name for w in warehouses}
    warehouse_data = [{"warehouse_id": wid, "warehouse_name": wh_map.get(wid, "Sin depósito"), **data} for wid, data in by_warehouse.items()]

    return {
        "total_items": total_items,
        "total_stock_units": round(total_stock, 2),
        "total_value": round(total_value, 2),
        "critical_count": len(critical),
        "over_count": len(over),
        "critical_items": critical[:20],
        "over_items": over[:20],
        "by_warehouse": warehouse_data,
        "by_category": [{"category": k or "Sin categoría", **v} for k, v in by_category.items()],
        "by_type": [{"type": k, **v} for k, v in by_type.items()],
        "warehouses_count": len(warehouses),
    }

# ─── PRODUCTS DASHBOARD ───
@router.get("/products")
def products_dashboard(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    invoices = db.query(Invoice).all()

    total = len(products)
    active = sum(1 for p in products if p.is_active)
    inactive = total - active

    by_type = {}
    by_category = {}
    by_family = {}
    price_ranges = {"0-1000": 0, "1000-5000": 0, "5000-10000": 0, "10000-50000": 0, "50000+": 0}

    for p in products:
        t = p.type or "product"
        by_type.setdefault(t, {"count": 0, "avg_price": 0, "total_price": 0})
        by_type[t]["count"] += 1
        by_type[t]["total_price"] += float(p.price or 0)

        cat = p.category or "Sin categoría"
        by_category.setdefault(cat, {"count": 0, "total_price": 0})
        by_category[cat]["count"] += 1
        by_category[cat]["total_price"] += float(p.price or 0)

        fam = p.family or "Sin familia"
        by_family.setdefault(fam, {"count": 0})
        by_family[fam]["count"] += 1

        price = float(p.price or 0)
        if price < 1000: price_ranges["0-1000"] += 1
        elif price < 5000: price_ranges["1000-5000"] += 1
        elif price < 10000: price_ranges["5000-10000"] += 1
        elif price < 50000: price_ranges["10000-50000"] += 1
        else: price_ranges["50000+"] += 1

    for t in by_type:
        by_type[t]["avg_price"] = round(by_type[t]["total_price"] / by_type[t]["count"], 2) if by_type[t]["count"] > 0 else 0

    avg_price = round(sum(float(p.price or 0) for p in products) / total if total > 0 else 0, 2)
    max_price_prod = max(products, key=lambda p: float(p.price or 0)) if products else None
    min_price_prod = min(products, key=lambda p: float(p.price or 0)) if products else None

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "avg_price": avg_price,
        "max_price": {"name": max_price_prod.name, "price": float(max_price_prod.price or 0)} if max_price_prod else None,
        "min_price": {"name": min_price_prod.name, "price": float(min_price_prod.price or 0)} if min_price_prod else None,
        "by_type": [{"type": k, **v} for k, v in by_type.items()],
        "by_category": [{"category": k, **v} for k, v in sorted(by_category.items(), key=lambda x: x[1]["count"], reverse=True)],
        "by_family": [{"family": k, **v} for k, v in sorted(by_family.items(), key=lambda x: x[1]["count"], reverse=True)],
        "price_ranges": [{"range": k, "count": v} for k, v in price_ranges.items()],
    }

# ─── PROVIDERS DASHBOARD ───
@router.get("/providers")
def providers_dashboard(db: Session = Depends(get_db)):
    from app.models.service_payment import ServicePayment

    providers = db.query(Provider).all()
    services = db.query(ProviderService).all()
    payments = db.query(ServicePayment).all()
    now = datetime.now()
    usd_rate = get_latest_usd_rate(db)

    total = len(providers)
    active = sum(1 for p in providers if p.is_active)
    active_services = sum(1 for s in services if s.status == "Active")

    # Build service→provider mapping
    svc_to_prov = {s.id: s.provider_id for s in services}
    svc_cost = {s.id: float(s.cost_price or 0) for s in services}
    svc_cycle = {s.id: s.billing_cycle for s in services}

    # Total paid historically
    total_paid = sum(pay_ars(p) for p in payments)

    # Expected monthly cost (converted to ARS)
    total_monthly_all = sum(svc_cost_ars(s, usd_rate) for s in services if s.billing_cycle == "Monthly" and s.status == "Active")
    total_yearly_all = sum(svc_cost_ars(s, usd_rate) for s in services if s.billing_cycle == "Yearly" and s.status == "Active")
    expected_monthly = total_monthly_all + (total_yearly_all / 12)

    # Timeline: last 12 months - per provider per month
    timeline = []
    for m_offset in range(11, -1, -1):
        dt = now - timedelta(days=30 * m_offset)
        month = dt.month
        year = dt.year
        month_label = dt.strftime("%b %Y")

        # Expected costs per provider this month (in ARS)
        month_expected = {}
        for s in services:
            if s.status != "Active":
                continue
            pid = s.provider_id
            cost = svc_cost_ars(s, usd_rate)
            if s.billing_cycle == "Monthly":
                month_expected[pid] = month_expected.get(pid, 0) + cost
            elif s.billing_cycle == "Yearly":
                month_expected[pid] = month_expected.get(pid, 0) + (cost / 12)

        # Actual payments per provider this month
        month_paid = {}
        for p in payments:
            if p.period_month == month and p.period_year == year:
                pid = svc_to_prov.get(p.provider_service_id, 0)
                month_paid[pid] = month_paid.get(pid, 0) + pay_ars(p)

        # Build per-provider data for this month
        providers_month = []
        for prov in providers:
            expected = round(month_expected.get(prov.id, 0), 2)
            paid = round(month_paid.get(prov.id, 0), 2)
            pending = round(max(expected - paid, 0), 2)
            if expected > 0 or paid > 0:
                providers_month.append({
                    "provider_id": prov.id,
                    "provider_name": prov.name,
                    "expected": expected,
                    "paid": paid,
                    "pending": pending,
                })

        total_month_expected = round(sum(v for v in month_expected.values()), 2)
        total_month_paid = round(sum(v for v in month_paid.values()), 2)

        timeline.append({
            "month": month_label,
            "month_num": month,
            "year": year,
            "total_expected": total_month_expected,
            "total_paid": total_month_paid,
            "total_pending": round(max(total_month_expected - total_month_paid, 0), 2),
            "providers": providers_month,
        })

    # Per-provider aggregated data
    provider_data = []
    for prov in providers:
        prov_services = [s for s in services if s.provider_id == prov.id]
        prov_payments = [p for p in payments if svc_to_prov.get(p.provider_service_id) == prov.id]

        monthly_cost = sum(svc_cost_ars(s, usd_rate) for s in prov_services if s.billing_cycle == "Monthly")
        yearly_cost = sum(svc_cost_ars(s, usd_rate) for s in prov_services if s.billing_cycle == "Yearly")
        total_monthly = monthly_cost + (yearly_cost / 12)
        total_paid_prov = sum(pay_ars(p) for p in prov_payments)

        # Current month paid/pending
        current_month_payments = [p for p in prov_payments if p.period_month == now.month and p.period_year == now.year]
        current_paid = sum(pay_ars(p) for p in current_month_payments)
        current_pending = max(total_monthly - current_paid, 0)

        provider_data.append({
            "id": prov.id, "name": prov.name, "is_active": prov.is_active,
            "service_count": len(prov_services),
            "monthly_cost": round(total_monthly, 2),
            "total_paid": round(total_paid_prov, 2),
            "current_paid": round(current_paid, 2),
            "current_pending": round(current_pending, 2),
            "payment_count": len(prov_payments),
        })

    provider_data.sort(key=lambda x: x["monthly_cost"], reverse=True)

    # Current month totals
    current_month_paid = sum(pay_ars(p) for p in payments if p.period_month == now.month and p.period_year == now.year)
    current_month_pending = max(expected_monthly - current_month_paid, 0)

    return {
        "total": total,
        "active": active,
        "inactive": total - active,
        "total_services": len(services),
        "active_services": active_services,
        "total_monthly_cost": round(expected_monthly, 2),
        "total_paid_all_time": round(total_paid, 2),
        "current_month_paid": round(current_month_paid, 2),
        "current_month_pending": round(current_month_pending, 2),
        "current_month": now.strftime("%b %Y"),
        "providers": provider_data,
        "timeline": timeline,
        "latest_usd_rate": usd_rate,
    }

# ─── CRM OVERVIEW ───
@router.get("/crm")
def crm_dashboard(db: Session = Depends(get_db)):
    clients = db.query(Client).all()
    quotes = db.query(Quote).all()
    invoices = db.query(Invoice).all()
    contacts = db.query(Contact).all()
    remitos = db.query(DeliveryNote).all()

    active_clients = sum(1 for c in clients if c.is_active)
    total_quoted = sum(float(q.total_amount or 0) for q in quotes)
    total_invoiced = sum(inv_ars(i) for i in invoices)
    conversion_rate = round((len(invoices) / len(quotes) * 100) if quotes else 0, 1)

    # Client ranking
    client_ranking = []
    for c in clients:
        c_invoices = [i for i in invoices if i.client_id == c.id]
        c_quotes = [q for q in quotes if q.client_id == c.id]
        c_remitos = [r for r in remitos if r.client_id == c.id]
        c_contacts = [ct for ct in contacts if ct.client_id == c.id]
        total = sum(inv_ars(i) for i in c_invoices)
        client_ranking.append({
            "id": c.id, "name": c.name, "is_active": c.is_active,
            "invoice_count": len(c_invoices), "invoice_total": round(total, 2),
            "quote_count": len(c_quotes), "remito_count": len(c_remitos),
            "contact_count": len(c_contacts),
        })
    client_ranking.sort(key=lambda x: x["invoice_total"], reverse=True)

    # Quote statuses
    quote_statuses = {}
    for q in quotes:
        s = q.status or "draft"
        quote_statuses.setdefault(s, {"count": 0, "amount": 0})
        quote_statuses[s]["count"] += 1
        quote_statuses[s]["amount"] += float(q.total_amount or 0)

    # Monthly timeline for CRM (quotes + invoices)
    now = datetime.now()
    crm_monthly = []
    for m_offset in range(11, -1, -1):
        dt = now - timedelta(days=30 * m_offset)
        month = dt.month
        year = dt.year
        month_label = dt.strftime("%b %Y")
        m_quoted = sum(float(q.total_amount or 0) for q in quotes
                       if safe_month(q.created_at) == month and safe_year(q.created_at) == year)
        m_invoiced = sum(inv_ars(i) for i in invoices
                         if safe_month(i.issue_date) == month and safe_year(i.issue_date) == year)
        crm_monthly.append({"month": month_label, "quoted": round(m_quoted, 2), "invoiced": round(m_invoiced, 2)})

    return {
        "total_clients": len(clients),
        "active_clients": active_clients,
        "total_contacts": len(contacts),
        "total_quotes": len(quotes),
        "total_quoted": round(total_quoted, 2),
        "total_invoices": len(invoices),
        "total_invoiced": round(total_invoiced, 2),
        "total_remitos": len(remitos),
        "conversion_rate": conversion_rate,
        "client_ranking": client_ranking,
        "quote_statuses": [{"status": k, **v} for k, v in quote_statuses.items()],
        "monthly": crm_monthly,
    }

# ─── CASHFLOW DASHBOARD ───
@router.get("/cashflow")
def cashflow_dashboard(db: Session = Depends(get_db)):
    from app.models.service_payment import ServicePayment

    invoices = db.query(Invoice).all()
    service_payments = db.query(ServicePayment).all()
    payment_orders = db.query(PaymentOrder).all()
    purchase_orders = db.query(PurchaseOrder).all()
    services = db.query(ProviderService).all()
    now = datetime.now()
    usd_rate = get_latest_usd_rate(db)

    # ── INCOME: from paid invoices (status_id=3) ──
    paid_invoices = [i for i in invoices if i.status_id == 3]
    total_income = sum(inv_ars(i) for i in paid_invoices)
    pending_income = sum(inv_ars(i) for i in invoices if i.status_id in [1, 2, 4, 8])

    # ── EXPENSES: service payments + payment orders ──
    total_service_expense = sum(pay_ars(p) for p in service_payments)
    total_po_expense = sum(float(p.amount or 0) for p in payment_orders)
    total_expenses = total_service_expense + total_po_expense

    # Expected monthly service cost (converted to ARS)
    monthly_svc_cost = sum(svc_cost_ars(s, usd_rate) for s in services if s.billing_cycle == "Monthly" and s.status == "Active")
    yearly_svc_cost = sum(svc_cost_ars(s, usd_rate) for s in services if s.billing_cycle == "Yearly" and s.status == "Active")
    expected_monthly_expense = monthly_svc_cost + (yearly_svc_cost / 12)

    # Net
    net_cashflow = total_income - total_expenses

    # ── Monthly timeline (last 12 months) ──
    timeline = []
    running_balance = 0
    for m_offset in range(11, -1, -1):
        dt = now - timedelta(days=30 * m_offset)
        month = dt.month
        year = dt.year
        month_label = dt.strftime("%b %Y")

        month_income = sum(inv_ars(i) for i in paid_invoices
                          if safe_month(i.issue_date) == month and safe_year(i.issue_date) == year)

        month_pending_income = sum(inv_ars(i) for i in invoices
                                   if i.status_id in [1, 2, 4, 8]
                                   and safe_month(i.issue_date) == month and safe_year(i.issue_date) == year)

        # Service payment expenses this month
        month_svc_expense = sum(pay_ars(p) for p in service_payments
                                if p.period_month == month and p.period_year == year)

        # Payment order expenses this month
        month_po_expense = sum(float(p.amount or 0) for p in payment_orders
                               if safe_month(p.date) == month and safe_year(p.date) == year)

        month_total_expense = month_svc_expense + month_po_expense
        month_net = month_income - month_total_expense
        running_balance += month_net

        timeline.append({
            "month": month_label,
            "month_num": month,
            "year": year,
            "income": round(month_income, 2),
            "pending_income": round(month_pending_income, 2),
            "services_expense": round(month_svc_expense, 2),
            "other_expense": round(month_po_expense, 2),
            "total_expense": round(month_total_expense, 2),
            "net": round(month_net, 2),
            "balance": round(running_balance, 2),
        })

    # ── Expense breakdown by category ──
    expense_categories = {}
    for p in service_payments:
        svc = next((s for s in services if s.id == p.provider_service_id), None)
        if svc:
            provider = next((pr for pr in db.query(Provider).filter(Provider.id == svc.provider_id)), None)
            cat_name = provider.name if provider else "Otros"
        else:
            cat_name = "Otros"
        expense_categories[cat_name] = expense_categories.get(cat_name, 0) + pay_ars(p)

    expense_breakdown = [{"category": k, "amount": round(v, 2)}
                         for k, v in sorted(expense_categories.items(), key=lambda x: x[1], reverse=True)]

    # ── Income breakdown by client ──
    income_by_client = {}
    for i in paid_invoices:
        client_name = i.client.name if hasattr(i, 'client') and i.client else "Sin cliente"
        income_by_client[client_name] = income_by_client.get(client_name, 0) + inv_ars(i)

    income_breakdown = [{"client": k, "amount": round(v, 2)}
                        for k, v in sorted(income_by_client.items(), key=lambda x: x[1], reverse=True)]

    # Current month
    current_tl = timeline[-1] if timeline else {}

    # ── Commission data ──
    quotes = db.query(Quote).all()
    total_commissions = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in quotes if q.commission_pct)
    accepted_commissions = sum(float(q.total_amount or 0) * float(q.commission_pct or 0) / 100 for q in quotes if q.commission_pct and q.status == "Accepted")

    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_cashflow": round(net_cashflow, 2),
        "pending_income": round(pending_income, 2),
        "expected_monthly_expense": round(expected_monthly_expense, 2),
        "current_month": now.strftime("%b %Y"),
        "current_month_income": current_tl.get("income", 0),
        "current_month_expense": current_tl.get("total_expense", 0),
        "current_month_net": current_tl.get("net", 0),
        "running_balance": current_tl.get("balance", 0),
        "timeline": timeline,
        "expense_breakdown": expense_breakdown,
        "income_breakdown": income_breakdown,
        "total_commissions": round(total_commissions, 2),
        "accepted_commissions": round(accepted_commissions, 2),
        "latest_usd_rate": usd_rate,
    }

# ─── RRHH / PAYROLL DASHBOARD ───
@router.get("/rrhh")
def rrhh_dashboard(db: Session = Depends(get_db)):
    from app.models.employee import Employee
    from app.models.payroll import PayrollPeriod, PayrollSlip, PayrollSlipItem, PayrollConcept
    from app.models.time_entry import TimeEntry

    employees = db.query(Employee).all()
    periods = db.query(PayrollPeriod).all()
    slips = db.query(PayrollSlip).all()
    now = datetime.now()

    total_employees = len(employees)
    active_employees = sum(1 for e in employees if e.is_active)
    inactive_employees = total_employees - active_employees

    # Average salary (active employees with salary > 0)
    salaries = [float(e.salary) for e in employees if e.is_active and e.salary and float(e.salary) > 0]
    avg_salary = round(sum(salaries) / len(salaries), 2) if salaries else 0
    max_salary = round(max(salaries), 2) if salaries else 0
    min_salary = round(min(salaries), 2) if salaries else 0
    total_payroll = round(sum(salaries), 2)

    # Total deductions and employer cost from latest period
    latest_period = None
    for p in sorted(periods, key=lambda x: (x.year, x.month), reverse=True):
        if p.status in ("confirmed", "paid"):
            latest_period = p
            break
    if not latest_period:
        # Use any period
        for p in sorted(periods, key=lambda x: (x.year, x.month), reverse=True):
            latest_period = p
            break

    latest_slips = [s for s in slips if latest_period and s.period_id == latest_period.id]
    latest_total_net = sum(float(s.net_salary or 0) for s in latest_slips)
    latest_total_deductions = sum(float(s.total_deductions or 0) for s in latest_slips)
    latest_total_employer = sum(float(s.total_employer_cost or 0) for s in latest_slips)
    latest_total_gross = sum(float(s.gross_salary or 0) for s in latest_slips)

    # By department
    dept_count = {}
    dept_cost = {}
    for e in employees:
        if not e.is_active:
            continue
        dept = e.department or "Sin departamento"
        dept_count[dept] = dept_count.get(dept, 0) + 1
        dept_cost[dept] = dept_cost.get(dept, 0) + float(e.salary or 0)
    by_department = [{"department": k, "count": dept_count[k], "total_salary": round(dept_cost.get(k, 0), 2)}
                     for k in sorted(dept_count.keys(), key=lambda x: dept_count[x], reverse=True)]

    # By contract type
    contract_count = {}
    for e in employees:
        if not e.is_active:
            continue
        ct = e.contract_type or "permanent"
        contract_count[ct] = contract_count.get(ct, 0) + 1
    by_contract = [{"type": k, "count": v} for k, v in contract_count.items()]

    # Seniority distribution
    seniority = {"< 1 año": 0, "1-3 años": 0, "3-5 años": 0, "5-10 años": 0, "10+ años": 0}
    for e in employees:
        if not e.is_active or not e.hire_date:
            continue
        hd = e.hire_date if isinstance(e.hire_date, date_type) else e.hire_date.date() if hasattr(e.hire_date, 'date') else None
        if not hd:
            continue
        years = (now.date() - hd).days / 365.25
        if years < 1: seniority["< 1 año"] += 1
        elif years < 3: seniority["1-3 años"] += 1
        elif years < 5: seniority["3-5 años"] += 1
        elif years < 10: seniority["5-10 años"] += 1
        else: seniority["10+ años"] += 1

    # Monthly timeline: per-employee payroll cost over last 12 months
    emp_map = {e.id: e for e in employees}
    timeline = []
    for m_offset in range(11, -1, -1):
        dt = now - timedelta(days=30 * m_offset)
        month = dt.month
        year = dt.year
        month_label = dt.strftime("%b %Y")

        # Find period for this month
        period = None
        for p in periods:
            if p.year == year and p.month == month:
                period = p
                break

        month_slips = [s for s in slips if period and s.period_id == period.id] if period else []
        total_gross = sum(float(s.gross_salary or 0) for s in month_slips)
        total_net = sum(float(s.net_salary or 0) for s in month_slips)
        total_ded = sum(float(s.total_deductions or 0) for s in month_slips)
        total_emp_cost = sum(float(s.total_employer_cost or 0) for s in month_slips)
        emp_count = len(month_slips)

        # Per-employee breakdowns for this month
        employees_month = []
        for s in month_slips:
            emp = emp_map.get(s.employee_id)
            employees_month.append({
                "employee_id": s.employee_id,
                "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "?",
                "gross": round(float(s.gross_salary or 0), 2),
                "net": round(float(s.net_salary or 0), 2),
                "deductions": round(float(s.total_deductions or 0), 2),
                "employer_cost": round(float(s.total_employer_cost or 0), 2),
            })

        timeline.append({
            "month": month_label,
            "month_num": month,
            "year": year,
            "total_gross": round(total_gross, 2),
            "total_net": round(total_net, 2),
            "total_deductions": round(total_ded, 2),
            "total_employer_cost": round(total_emp_cost, 2),
            "employee_count": emp_count,
            "employees": employees_month,
        })

    # Employee ranking (by salary)
    employee_ranking = []
    for e in employees:
        if not e.is_active:
            continue
        # Count slips for this employee
        emp_slips = [s for s in slips if s.employee_id == e.id]
        total_paid_net = sum(float(s.net_salary or 0) for s in emp_slips if s.status == "paid")
        employee_ranking.append({
            "id": e.id,
            "name": f"{e.first_name} {e.last_name}",
            "legajo": e.legajo,
            "department": e.department or "—",
            "position": e.position or "—",
            "salary": round(float(e.salary or 0), 2),
            "contract_type": e.contract_type or "permanent",
            "hire_date": e.hire_date.isoformat() if e.hire_date else None,
            "total_paid_net": round(total_paid_net, 2),
            "slips_count": len(emp_slips),
        })
    employee_ranking.sort(key=lambda x: x["salary"], reverse=True)

    # Period status summary
    period_summary = []
    for p in sorted(periods, key=lambda x: (x.year, x.month), reverse=True)[:6]:
        p_slips = [s for s in slips if s.period_id == p.id]
        period_summary.append({
            "id": p.id,
            "description": f"{['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][p.month]} {p.year}",
            "status": p.status,
            "slip_count": len(p_slips),
            "total_net": round(sum(float(s.net_salary or 0) for s in p_slips), 2),
            "total_gross": round(sum(float(s.gross_salary or 0) for s in p_slips), 2),
            "total_employer_cost": round(sum(float(s.total_employer_cost or 0) for s in p_slips), 2),
        })

    # Time tracking summary
    entries = db.query(TimeEntry).all()
    total_check_ins = sum(1 for e in entries if e.entry_type == "check_in")

    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "inactive_employees": inactive_employees,
        "avg_salary": avg_salary,
        "max_salary": max_salary,
        "min_salary": min_salary,
        "total_payroll": total_payroll,
        "latest_period_description": f"{['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'][latest_period.month]} {latest_period.year}" if latest_period else "—",
        "latest_total_gross": round(latest_total_gross, 2),
        "latest_total_net": round(latest_total_net, 2),
        "latest_total_deductions": round(latest_total_deductions, 2),
        "latest_total_employer": round(latest_total_employer, 2),
        "by_department": by_department,
        "by_contract": by_contract,
        "seniority": [{"range": k, "count": v} for k, v in seniority.items()],
        "timeline": timeline,
        "employee_ranking": employee_ranking,
        "period_summary": period_summary,
        "total_check_ins": total_check_ins,
    }

