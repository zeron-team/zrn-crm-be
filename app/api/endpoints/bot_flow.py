from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.bot_flow import BotFlow
from app.schemas.bot_flow import BotFlowCreate, BotFlowUpdate, BotFlowResponse

router = APIRouter()


@router.get("/", response_model=List[BotFlowResponse])
def list_bot_flows(db: Session = Depends(get_db)):
    return db.query(BotFlow).order_by(BotFlow.updated_at.desc()).all()


@router.get("/active", response_model=List[BotFlowResponse])
def list_active_bot_flows(db: Session = Depends(get_db)):
    """Used by the WhatsApp service to get all active flows."""
    return db.query(BotFlow).filter(BotFlow.is_active == True).all()


@router.get("/{flow_id}", response_model=BotFlowResponse)
def get_bot_flow(flow_id: int, db: Session = Depends(get_db)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Bot flow not found")
    return flow


@router.post("/", response_model=BotFlowResponse)
def create_bot_flow(flow_in: BotFlowCreate, db: Session = Depends(get_db)):
    db_flow = BotFlow(**flow_in.model_dump())
    db.add(db_flow)
    db.commit()
    db.refresh(db_flow)
    return db_flow


@router.put("/{flow_id}", response_model=BotFlowResponse)
def update_bot_flow(flow_id: int, flow_in: BotFlowUpdate, db: Session = Depends(get_db)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Bot flow not found")
    update_data = flow_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(flow, field, value)
    db.commit()
    db.refresh(flow)
    return flow


@router.delete("/{flow_id}", response_model=BotFlowResponse)
def delete_bot_flow(flow_id: int, db: Session = Depends(get_db)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Bot flow not found")
    db.delete(flow)
    db.commit()
    return flow


@router.post("/{flow_id}/toggle", response_model=BotFlowResponse)
def toggle_bot_flow(flow_id: int, db: Session = Depends(get_db)):
    flow = db.query(BotFlow).filter(BotFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Bot flow not found")
    flow.is_active = not flow.is_active
    db.commit()
    db.refresh(flow)
    return flow
