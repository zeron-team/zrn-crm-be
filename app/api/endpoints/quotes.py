from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.quote import quote_repository
from app.schemas.quote import QuoteCreate, QuoteUpdate, QuoteResponse

router = APIRouter()

@router.get("/", response_model=List[QuoteResponse])
def read_quotes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    quotes = quote_repository.get_multi(db, skip=skip, limit=limit)
    return quotes

@router.post("/", response_model=QuoteResponse)
def create_quote(
    *,
    db: Session = Depends(get_db),
    quote_in: QuoteCreate,
) -> Any:
    quote = quote_repository.create(db=db, obj_in=quote_in)
    return quote

@router.get("/{id}", response_model=QuoteResponse)
def read_quote(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    quote = quote_repository.get(db=db, id=id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote

@router.put("/{id}", response_model=QuoteResponse)
def update_quote(
    *,
    db: Session = Depends(get_db),
    id: int,
    quote_in: QuoteUpdate,
) -> Any:
    quote = quote_repository.get(db=db, id=id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    quote = quote_repository.update(db=db, db_obj=quote, obj_in=quote_in)
    return quote

@router.delete("/{id}", response_model=QuoteResponse)
def delete_quote(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    quote = quote_repository.get(db=db, id=id)
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    quote = quote_repository.remove(db=db, id=id)
    return quote
