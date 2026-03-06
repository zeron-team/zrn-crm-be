from sqlalchemy.orm import Session
from app.repositories.invoice import invoice_repository, invoice_status_repository
from app.models.invoice_item import InvoiceItem
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceStatusCreate, InvoiceStatusUpdate
from fastapi import HTTPException, status
from decimal import Decimal

def _compute_amount_ars(invoice_data: dict) -> dict:
    """Auto-compute amount_ars from amount, currency, exchange_rate."""
    amount = Decimal(str(invoice_data.get('amount', 0) or 0))
    currency = invoice_data.get('currency', 'ARS')
    exchange_rate = Decimal(str(invoice_data.get('exchange_rate', 1) or 1))
    if currency == 'ARS':
        invoice_data['exchange_rate'] = Decimal('1')
        invoice_data['amount_ars'] = amount
    else:
        invoice_data['exchange_rate'] = exchange_rate
        invoice_data['amount_ars'] = round(amount * exchange_rate, 2)
    return invoice_data

class InvoiceService:
    def create_invoice(self, db: Session, invoice_in: InvoiceCreate):
        items_data = invoice_in.items
        invoice_data = _compute_amount_ars(invoice_in.dict(exclude={"items"}))
        db_obj = Invoice(**invoice_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        if items_data:
            for item in items_data:
                db_item = InvoiceItem(**item.dict(), invoice_id=db_obj.id)
                db.add(db_item)
            db.commit()
            db.refresh(db_obj)
            
        return db_obj

    def get_invoice(self, db: Session, invoice_id: int):
        invoice = invoice_repository.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice
        
    def get_invoices(self, db: Session, skip: int = 0, limit: int = 100):
        return invoice_repository.get_multi(db, skip=skip, limit=limit)

    def update_invoice(self, db: Session, invoice_id: int, invoice_in: InvoiceUpdate):
        invoice = invoice_repository.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        update_data = invoice_in.dict(exclude_unset=True, exclude={"items"})
        
        # Recompute amount_ars if amount or currency or exchange_rate changed
        if 'amount' in update_data or 'currency' in update_data or 'exchange_rate' in update_data:
            merged = {
                'amount': update_data.get('amount', invoice.amount),
                'currency': update_data.get('currency', invoice.currency),
                'exchange_rate': update_data.get('exchange_rate', invoice.exchange_rate or 1),
            }
            computed = _compute_amount_ars(merged)
            update_data['exchange_rate'] = computed['exchange_rate']
            update_data['amount_ars'] = computed['amount_ars']
        
        for field, value in update_data.items():
            setattr(invoice, field, value)
            
        if invoice_in.items is not None:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
            for item in invoice_in.items:
                db_item = InvoiceItem(**item.dict(), invoice_id=invoice_id)
                db.add(db_item)
                
        db.commit()
        db.refresh(invoice)
        return invoice

    def delete_invoice(self, db: Session, invoice_id: int):
        invoice = invoice_repository.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        return invoice_repository.remove(db, id=invoice_id)

    def update_file_url(self, db: Session, invoice_id: int, file_url: str):
        invoice = invoice_repository.get(db, id=invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        invoice.file_url = file_url
        db.commit()
        db.refresh(invoice)
        return invoice

class InvoiceStatusService:
    def create_status(self, db: Session, status_in: InvoiceStatusCreate):
        return invoice_status_repository.create(db, obj_in=status_in)

    def get_statuses(self, db: Session, skip: int = 0, limit: int = 100):
        return invoice_status_repository.get_multi(db, skip=skip, limit=limit)

    def update_status(self, db: Session, status_id: int, status_in: InvoiceStatusUpdate):
        status_obj = invoice_status_repository.get(db, id=status_id)
        if not status_obj:
            raise HTTPException(status_code=404, detail="Invoice Status not found")
        return invoice_status_repository.update(db, db_obj=status_obj, obj_in=status_in)

    def delete_status(self, db: Session, status_id: int):
        status_obj = invoice_status_repository.get(db, id=status_id)
        if not status_obj:
            raise HTTPException(status_code=404, detail="Invoice Status not found")
        return invoice_status_repository.remove(db, id=status_id)

invoice_service = InvoiceService()
invoice_status_service = InvoiceStatusService()
