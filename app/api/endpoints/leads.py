from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.lead import lead_repository
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.models.client import Client
from app.models.quote import Quote

router = APIRouter()

@router.get("/", response_model=List[LeadResponse])
def read_leads(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    leads = lead_repository.get_multi(db, skip=skip, limit=limit)
    return leads

@router.post("/", response_model=LeadResponse)
def create_lead(
    *,
    db: Session = Depends(get_db),
    lead_in: LeadCreate,
) -> Any:
    lead = lead_repository.create(db=db, obj_in=lead_in)
    return lead

@router.get("/{id}", response_model=LeadResponse)
def read_lead(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    lead = lead_repository.get(db=db, id=id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.put("/{id}", response_model=LeadResponse)
def update_lead(
    *,
    db: Session = Depends(get_db),
    id: int,
    lead_in: LeadUpdate,
) -> Any:
    lead = lead_repository.get(db=db, id=id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = lead_repository.update(db=db, db_obj=lead, obj_in=lead_in)
    return lead

@router.delete("/{id}", response_model=LeadResponse)
def delete_lead(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    lead = lead_repository.get(db=db, id=id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead = lead_repository.delete(db=db, id=id)
    return lead


@router.post("/{id}/convert-to-client")
def convert_lead_to_client(
    *,
    db: Session = Depends(get_db),
    id: int,
) -> Any:
    """Convert a lead (prospecto) into a client (cuenta), copying all shared fields."""
    lead = lead_repository.get(db=db, id=id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if lead.status == "Converted":
        raise HTTPException(status_code=400, detail="Lead already converted")

    # Create client from lead data
    new_client = Client(
        name=lead.company_name,
        email=lead.email,
        phone=lead.phone,
        address=lead.address,
        city=lead.city,
        province=lead.province,
        country=lead.country or "Argentina",
        website=lead.website,
        is_active=True,
    )
    db.add(new_client)
    db.flush()  # get the new client id

    # Update all quotes linked to this lead → link to the new client
    db.query(Quote).filter(Quote.lead_id == lead.id).update(
        {Quote.client_id: new_client.id, Quote.lead_id: None},
        synchronize_session="fetch"
    )

    # Mark lead as converted
    lead.status = "Converted"
    db.commit()
    db.refresh(new_client)

    return {
        "success": True,
        "client_id": new_client.id,
        "client_name": new_client.name,
        "message": f"Lead '{lead.company_name}' converted to client successfully"
    }

