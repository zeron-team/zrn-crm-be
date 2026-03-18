"""
Sales Orders (Órdenes de Pedido) — CRUD API
Flow: Quote(Accepted) → SalesOrder → Invoice  OR  Manual creation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from app.database import get_db
from app.models.sales_order import SalesOrder, SalesOrderStatus
from app.models.sales_order_item import SalesOrderItem
from app.models.quote import Quote
from app.models.invoice import Invoice
from app.schemas.sales_order import (
    SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse, SalesOrderItemResponse
)

router = APIRouter(prefix="/sales-orders", tags=["sales_orders"])


def _next_order_number(db: Session) -> str:
    last = db.query(SalesOrder).order_by(SalesOrder.id.desc()).first()
    if last and last.order_number:
        import re
        m = re.search(r"(\d+)", last.order_number)
        num = int(m.group(1)) + 1 if m else 1
    else:
        num = 1
    return f"PD-{str(num).zfill(5)}"


def _load_with_relations(db: Session, order_id: int) -> SalesOrder:
    return db.query(SalesOrder).options(
        joinedload(SalesOrder.client),
        joinedload(SalesOrder.seller),
        joinedload(SalesOrder.quote),
        joinedload(SalesOrder.items),
    ).filter(SalesOrder.id == order_id).first()


def _enrich(so: SalesOrder, db: Session = None) -> dict:
    """Convert SalesOrder ORM object to enriched dict for response"""
    invoice_count = 0
    if db:
        invoice_count = db.query(Invoice).filter(Invoice.sales_order_id == so.id).count()
    elif hasattr(so, 'invoices') and so.invoices:
        invoice_count = len(so.invoices)
    return {
        "id": so.id,
        "order_number": so.order_number,
        "quote_id": so.quote_id,
        "client_id": so.client_id,
        "seller_id": so.seller_id,
        "status": so.status,
        "currency": so.currency,
        "subtotal": so.subtotal,
        "tax_amount": so.tax_amount,
        "total_amount": so.total_amount,
        "notes": so.notes,
        "delivery_date": so.delivery_date,
        "created_at": so.created_at,
        "updated_at": so.updated_at,
        "client_name": so.client.name if so.client else None,
        "seller_name": so.seller.full_name if so.seller and hasattr(so.seller, 'full_name') else (so.seller.username if so.seller else None),
        "quote_number": so.quote.quote_number if so.quote else None,
        "items": [
            {
                "id": item.id,
                "sales_order_id": item.sales_order_id,
                "product_id": item.product_id,
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
            }
            for item in (so.items or [])
        ],
        "invoice_count": invoice_count,
    }


def _sync_items(db: Session, so: SalesOrder, items_data: list):
    """Replace all items with new ones and recalculate totals"""
    # Delete existing items
    db.query(SalesOrderItem).filter(SalesOrderItem.sales_order_id == so.id).delete()
    db.flush()

    subtotal = 0
    for item_data in items_data:
        item = SalesOrderItem(
            sales_order_id=so.id,
            product_id=item_data.product_id if hasattr(item_data, 'product_id') else item_data.get('product_id'),
            description=item_data.description if hasattr(item_data, 'description') else item_data.get('description'),
            quantity=item_data.quantity if hasattr(item_data, 'quantity') else item_data.get('quantity'),
            unit_price=item_data.unit_price if hasattr(item_data, 'unit_price') else item_data.get('unit_price'),
            total_price=item_data.total_price if hasattr(item_data, 'total_price') else item_data.get('total_price'),
        )
        db.add(item)
        subtotal += float(item.total_price)

    so.subtotal = subtotal
    so.tax_amount = 0
    so.total_amount = subtotal


# ── Manual Create ──────────────────────────────────────────────
@router.post("/", response_model=SalesOrderResponse)
def create_sales_order(data: SalesOrderCreate, db: Session = Depends(get_db)):
    so = SalesOrder(
        order_number=_next_order_number(db),
        quote_id=data.quote_id,
        client_id=data.client_id,
        seller_id=data.seller_id,
        status=SalesOrderStatus.PENDING,
        currency=data.currency,
        subtotal=0,
        tax_amount=0,
        total_amount=0,
        notes=data.notes,
        delivery_date=data.delivery_date,
    )
    db.add(so)
    db.flush()

    if data.items:
        _sync_items(db, so, data.items)

    db.commit()
    db.refresh(so)
    so = _load_with_relations(db, so.id)
    return _enrich(so, db)


# ── Create from Quote ──────────────────────────────────────────
@router.post("/from-quote/{quote_id}", response_model=SalesOrderResponse)
def create_from_quote(quote_id: int, db: Session = Depends(get_db)):
    quote = db.query(Quote).options(
        joinedload(Quote.items),
        joinedload(Quote.client),
    ).filter(Quote.id == quote_id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    existing = db.query(SalesOrder).filter(SalesOrder.quote_id == quote_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un pedido (#{existing.order_number}) para este presupuesto")

    so = SalesOrder(
        order_number=_next_order_number(db),
        quote_id=quote.id,
        client_id=quote.client_id,
        seller_id=quote.seller_id,
        status=SalesOrderStatus.PENDING,
        currency=quote.currency,
        subtotal=quote.subtotal,
        tax_amount=quote.tax_amount,
        total_amount=quote.total_amount,
    )
    db.add(so)
    db.flush()

    for qi in (quote.items or []):
        item = SalesOrderItem(
            sales_order_id=so.id,
            product_id=qi.product_id,
            description=qi.description,
            quantity=qi.quantity,
            unit_price=qi.unit_price,
            total_price=qi.total_price,
        )
        db.add(item)

    db.commit()
    db.refresh(so)
    so = _load_with_relations(db, so.id)
    return _enrich(so, db)


# ── List ────────────────────────────────────────────────────────
@router.get("/", response_model=List[SalesOrderResponse])
def list_sales_orders(
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(SalesOrder).options(
        joinedload(SalesOrder.client),
        joinedload(SalesOrder.seller),
        joinedload(SalesOrder.quote),
        joinedload(SalesOrder.items),
    )
    if status:
        q = q.filter(SalesOrder.status == status)
    if client_id:
        q = q.filter(SalesOrder.client_id == client_id)

    orders = q.order_by(SalesOrder.updated_at.desc()).offset(skip).limit(limit).all()
    return [_enrich(so, db) for so in orders]


# ── Get Detail ──────────────────────────────────────────────────
@router.get("/{order_id}", response_model=SalesOrderResponse)
def get_sales_order(order_id: int, db: Session = Depends(get_db)):
    so = _load_with_relations(db, order_id)
    if not so:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return _enrich(so, db)


# ── Update (full editing) ──────────────────────────────────────
@router.put("/{order_id}", response_model=SalesOrderResponse)
def update_sales_order(order_id: int, data: SalesOrderUpdate, db: Session = Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if data.client_id is not None:
        so.client_id = data.client_id
    if data.seller_id is not None:
        so.seller_id = data.seller_id
    if data.quote_id is not None:
        so.quote_id = data.quote_id
    if data.status is not None:
        so.status = data.status
    if data.currency is not None:
        so.currency = data.currency
    if data.notes is not None:
        so.notes = data.notes
    if data.delivery_date is not None:
        so.delivery_date = data.delivery_date

    # If items provided, replace all items and recalculate totals
    if data.items is not None:
        _sync_items(db, so, data.items)

    db.commit()
    db.refresh(so)
    so = _load_with_relations(db, so.id)
    return _enrich(so, db)


# ── Delete ──────────────────────────────────────────────────────
@router.delete("/{order_id}")
def delete_sales_order(order_id: int, db: Session = Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.id == order_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    db.delete(so)
    db.commit()
    return {"ok": True, "deleted": order_id}


# ── Pipeline Summary ───────────────────────────────────────────
@router.get("/pipeline/summary")
def pipeline_summary(db: Session = Depends(get_db)):
    """Aggregated view of the entire sales funnel: quotes → orders → invoices"""
    from sqlalchemy import func
    from app.models.client import Client

    # ── Quotes by status ──
    quote_stats = (
        db.query(
            Quote.status,
            func.count(Quote.id).label("count"),
            func.coalesce(func.sum(Quote.total_amount), 0).label("total"),
        )
        .group_by(Quote.status)
        .all()
    )
    quotes_by_status = {row.status: {"count": row.count, "total": float(row.total)} for row in quote_stats}

    # Recent quotes (last 20)
    recent_quotes = (
        db.query(Quote)
        .options(joinedload(Quote.client))
        .order_by(Quote.id.desc())
        .limit(20)
        .all()
    )

    # ── Orders by status ──
    order_stats = (
        db.query(
            SalesOrder.status,
            func.count(SalesOrder.id).label("count"),
            func.coalesce(func.sum(SalesOrder.total_amount), 0).label("total"),
        )
        .group_by(SalesOrder.status)
        .all()
    )
    orders_by_status = {row.status: {"count": row.count, "total": float(row.total)} for row in order_stats}

    # Recent orders (last 20)
    recent_orders = (
        db.query(SalesOrder)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.quote))
        .order_by(SalesOrder.id.desc())
        .limit(20)
        .all()
    )

    # ── Invoices linked to orders ──
    linked_invoices = (
        db.query(Invoice)
        .filter(Invoice.sales_order_id.isnot(None))
        .options(joinedload(Invoice.client))
        .order_by(Invoice.id.desc())
        .limit(20)
        .all()
    )

    # ── Totals ──
    total_quotes = sum(v["total"] for v in quotes_by_status.values())
    total_orders = sum(v["total"] for v in orders_by_status.values())
    total_invoiced = sum(float(inv.amount or 0) for inv in linked_invoices)

    return {
        "quotes": {
            "by_status": quotes_by_status,
            "total_amount": total_quotes,
            "total_count": sum(v["count"] for v in quotes_by_status.values()),
            "recent": [
                {
                    "id": q.id, "quote_number": q.quote_number, "status": q.status,
                    "total_amount": float(q.total_amount), "currency": q.currency,
                    "client_name": q.client.name if q.client else None,
                    "issue_date": str(q.issue_date) if q.issue_date else None,
                    "expiry_date": str(q.expiry_date) if q.expiry_date else None,
                }
                for q in recent_quotes
            ],
        },
        "orders": {
            "by_status": orders_by_status,
            "total_amount": total_orders,
            "total_count": sum(v["count"] for v in orders_by_status.values()),
            "recent": [
                {
                    "id": o.id, "order_number": o.order_number, "status": o.status,
                    "total_amount": float(o.total_amount), "currency": o.currency,
                    "client_name": o.client.name if o.client else None,
                    "quote_number": o.quote.quote_number if o.quote else None,
                    "delivery_date": str(o.delivery_date) if o.delivery_date else None,
                }
                for o in recent_orders
            ],
        },
        "invoices": {
            "total_invoiced": total_invoiced,
            "count": len(linked_invoices),
            "recent": [
                {
                    "id": inv.id, "invoice_number": inv.invoice_number,
                    "amount": float(inv.amount), "currency": inv.currency,
                    "client_name": inv.client.name if inv.client else None,
                    "sales_order_id": inv.sales_order_id,
                }
                for inv in linked_invoices
            ],
        },
        "funnel": {
            "quotes_total": total_quotes,
            "orders_total": total_orders,
            "invoiced_total": total_invoiced,
            "conversion_quote_to_order": round(
                (sum(v["count"] for v in orders_by_status.values()) / max(sum(v["count"] for v in quotes_by_status.values()), 1)) * 100, 1
            ),
        },
    }

