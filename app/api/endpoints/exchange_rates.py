from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from app.database import get_db
from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


def get_rate_for_date(db: Session, payment_date, currency: str = "USD") -> float:
    """Get the exchange rate for a given date. Falls back to the most recent prior date."""
    from datetime import date as date_type, datetime
    if isinstance(payment_date, datetime):
        d = payment_date.date()
    elif isinstance(payment_date, date_type):
        d = payment_date
    else:
        return 1.0

    rate = db.query(ExchangeRate).filter(
        ExchangeRate.date <= d,
        ExchangeRate.currency == currency,
    ).order_by(ExchangeRate.date.desc()).first()

    if rate:
        return float(rate.sell_rate)
    return 1.0


@router.get("/", response_model=List[ExchangeRateResponse])
def list_exchange_rates(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    currency: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ExchangeRate)
    if from_date:
        q = q.filter(ExchangeRate.date >= from_date)
    if to_date:
        q = q.filter(ExchangeRate.date <= to_date)
    if currency:
        q = q.filter(ExchangeRate.currency == currency)
    return q.order_by(ExchangeRate.date.desc()).all()


@router.get("/latest", response_model=ExchangeRateResponse)
def get_latest(currency: str = "USD", db: Session = Depends(get_db)):
    rate = db.query(ExchangeRate).filter(
        ExchangeRate.currency == currency
    ).order_by(ExchangeRate.date.desc()).first()
    if not rate:
        raise HTTPException(status_code=404, detail="No exchange rate found")
    return rate


@router.get("/date/{rate_date}", response_model=ExchangeRateResponse)
def get_by_date(rate_date: date, currency: str = "USD", db: Session = Depends(get_db)):
    rate = db.query(ExchangeRate).filter(
        ExchangeRate.date == rate_date,
        ExchangeRate.currency == currency,
    ).first()
    if not rate:
        # Fallback to most recent prior
        rate = db.query(ExchangeRate).filter(
            ExchangeRate.date <= rate_date,
            ExchangeRate.currency == currency,
        ).order_by(ExchangeRate.date.desc()).first()
    if not rate:
        raise HTTPException(status_code=404, detail="No exchange rate found for this date")
    return rate


@router.post("/", response_model=ExchangeRateResponse)
def create_exchange_rate(payload: ExchangeRateCreate, db: Session = Depends(get_db)):
    # Check if already exists for this date+currency
    existing = db.query(ExchangeRate).filter(
        ExchangeRate.date == payload.date,
        ExchangeRate.currency == payload.currency,
    ).first()
    if existing:
        # Update instead of duplicate
        existing.buy_rate = payload.buy_rate
        existing.sell_rate = payload.sell_rate
        existing.source = payload.source
        existing.updated_by = payload.created_by
        db.commit()
        db.refresh(existing)
        return existing

    db_obj = ExchangeRate(**payload.model_dump())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.put("/{rate_id}", response_model=ExchangeRateResponse)
def update_exchange_rate(rate_id: int, payload: ExchangeRateUpdate, db: Session = Depends(get_db)):
    obj = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(obj, field, value)
    
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{rate_id}", response_model=ExchangeRateResponse)
def delete_exchange_rate(rate_id: int, db: Session = Depends(get_db)):
    obj = db.query(ExchangeRate).filter(ExchangeRate.id == rate_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Exchange rate not found")
    db.delete(obj)
    db.commit()
    return obj
