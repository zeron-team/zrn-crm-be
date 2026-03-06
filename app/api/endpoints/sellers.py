"""Sellers (Vendedores) dashboard and API."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.quote import Quote
from app.models.invoice import Invoice

router = APIRouter(prefix="/sellers", tags=["sellers"])


def user_to_seller(u: User, db: Session):
    """Build seller summary with stats."""
    quotes_q = db.query(Quote).filter(Quote.seller_id == u.id)
    invoices_q = db.query(Invoice).filter(Invoice.seller_id == u.id)
    clients_q = db.query(Client).filter(Client.seller_id == u.id)

    quote_count = quotes_q.count()
    quote_total = db.query(func.coalesce(func.sum(Quote.total_amount), 0)).filter(Quote.seller_id == u.id).scalar()

    inv_count = invoices_q.count()
    inv_total = db.query(func.coalesce(func.sum(Invoice.amount), 0)).filter(Invoice.seller_id == u.id).scalar()

    client_count = clients_q.count()

    # Breakdown by status
    accepted = quotes_q.filter(Quote.status == "Accepted").count()
    accepted_total = db.query(func.coalesce(func.sum(Quote.total_amount), 0)).filter(
        Quote.seller_id == u.id, Quote.status == "Accepted"
    ).scalar()
    rejected = quotes_q.filter(Quote.status == "Rejected").count()
    rejected_total = db.query(func.coalesce(func.sum(Quote.total_amount), 0)).filter(
        Quote.seller_id == u.id, Quote.status == "Rejected"
    ).scalar()
    sent = quotes_q.filter(Quote.status == "Sent").count()
    draft = quotes_q.filter(Quote.status == "Draft").count()

    # Clients won = clients that have at least one Accepted quote from this seller
    won_client_ids = db.query(Quote.client_id).filter(
        Quote.seller_id == u.id, Quote.status == "Accepted", Quote.client_id.isnot(None)
    ).distinct().all()
    clients_won = len(won_client_ids)

    return {
        "id": u.id,
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "commission_pct": float(u.commission_pct or 0),
        "data_complete": bool(u.commission_pct and u.commission_pct > 0),
        "stats": {
            "clients_assigned": client_count,
            "clients_won": clients_won,
            "quotes_total": quote_count,
            "quotes_accepted": accepted,
            "quotes_rejected": rejected,
            "quotes_sent": sent,
            "quotes_draft": draft,
            "quotes_amount": float(quote_total or 0),
            "quotes_accepted_amount": float(accepted_total or 0),
            "quotes_rejected_amount": float(rejected_total or 0),
            "invoices": inv_count,
            "invoices_total": float(inv_total or 0),
        }
    }


@router.get("/")
def list_sellers(db: Session = Depends(get_db)):
    """Return all users with role vendedor (supports comma-separated roles), with their sales stats."""
    sellers = db.query(User).filter(User.role.contains("vendedor")).all()
    return [user_to_seller(s, db) for s in sellers]


@router.get("/monthly-stats")
def monthly_stats(db: Session = Depends(get_db)):
    """Return monthly quote stats per seller for the last 12 months."""
    from datetime import date, timedelta
    from collections import defaultdict
    import calendar

    sellers = db.query(User).filter(User.role.contains("vendedor")).all()
    today = date.today()
    # Last 12 months
    months = []
    for i in range(11, -1, -1):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    result = []
    for y, m in months:
        month_label = f"{y}-{m:02d}"
        entry = {"month": month_label, "month_name": calendar.month_abbr[m]}
        for s in sellers:
            prefix = f"s{s.id}"
            name = s.full_name.split()[0] if s.full_name else f"V{s.id}"
            entry[f"{prefix}_name"] = name

            quotes = db.query(Quote).filter(
                Quote.seller_id == s.id,
                func.extract('year', Quote.issue_date) == y,
                func.extract('month', Quote.issue_date) == m,
            ).all()

            assigned = len(quotes)
            won = sum(1 for q in quotes if q.status == "Accepted")
            lost = sum(1 for q in quotes if q.status == "Rejected")
            amount_assigned = sum(float(q.total_amount or 0) for q in quotes)
            amount_won = sum(float(q.total_amount or 0) for q in quotes if q.status == "Accepted")
            amount_lost = sum(float(q.total_amount or 0) for q in quotes if q.status == "Rejected")

            entry[f"{prefix}_assigned"] = assigned
            entry[f"{prefix}_won"] = won
            entry[f"{prefix}_lost"] = lost
            entry[f"{prefix}_amount_assigned"] = amount_assigned
            entry[f"{prefix}_amount_won"] = amount_won
            entry[f"{prefix}_amount_lost"] = amount_lost

        result.append(entry)

    # Also return seller metadata for the chart legend
    seller_meta = [{"id": s.id, "prefix": f"s{s.id}", "name": s.full_name} for s in sellers]
    return {"months": result, "sellers": seller_meta}


@router.get("/{seller_id}")
def get_seller(seller_id: int, db: Session = Depends(get_db)):
    """Get a single seller with detailed info."""
    seller = db.query(User).filter(User.id == seller_id).first()
    if not seller:
        return {"error": "not found"}
    data = user_to_seller(seller, db)

    # All quotes with client info
    all_quotes = db.query(Quote).filter(Quote.seller_id == seller_id).order_by(Quote.created_at.desc()).all()
    clients_map = {}
    for c in db.query(Client).all():
        clients_map[c.id] = c.name

    data["quotes"] = [{
        "id": q.id,
        "quote_number": q.quote_number,
        "status": q.status,
        "total_amount": float(q.total_amount or 0),
        "commission_pct": float(q.commission_pct or 0),
        "commission_amount": float((q.total_amount or 0) * (q.commission_pct or 0) / 100),
        "client_id": q.client_id,
        "client_name": clients_map.get(q.client_id, "—") if q.client_id else "Sin cliente",
        "lead_id": q.lead_id,
        "issue_date": str(q.issue_date) if q.issue_date else None,
        "currency": q.currency,
    } for q in all_quotes]

    # Assigned clients
    my_clients = db.query(Client).filter(Client.seller_id == seller_id).all()
    data["clients"] = []
    for c in my_clients:
        cq = db.query(Quote).filter(Quote.seller_id == seller_id, Quote.client_id == c.id).all()
        total_q = len(cq)
        won = sum(1 for q in cq if q.status == "Accepted")
        lost = sum(1 for q in cq if q.status == "Rejected")
        pending = total_q - won - lost
        amount_won = sum(float(q.total_amount or 0) for q in cq if q.status == "Accepted")
        data["clients"].append({
            "id": c.id,
            "name": c.name,
            "cuit_dni": c.cuit_dni,
            "email": c.email,
            "quotes_total": total_q,
            "quotes_won": won,
            "quotes_lost": lost,
            "quotes_pending": pending,
            "amount_won": amount_won,
            "is_won": won > 0,
        })

    return data
