from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timezone

from app.database import get_db
from app.models.ticket import Ticket, TicketComment
from app.models.user import User
from app.models.client import Client
from app.schemas.ticket import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse,
    TicketCommentCreate, TicketCommentResponse,
)

router = APIRouter()


def _next_ticket_number(db: Session) -> str:
    last = db.query(Ticket).order_by(Ticket.id.desc()).first()
    num = (last.id + 1) if last else 1
    return f"TK-{num:05d}"


def _ticket_to_response(t: Ticket, include_comments=False):
    data = {
        "id": t.id,
        "ticket_number": t.ticket_number,
        "subject": t.subject,
        "description": t.description,
        "status": t.status,
        "priority": t.priority,
        "category": t.category,
        "ticket_type": t.ticket_type,
        "client_id": t.client_id,
        "assigned_to": t.assigned_to,
        "created_by": t.created_by,
        "estimated_hours": t.estimated_hours,
        "actual_hours": t.actual_hours,
        "estimated_date": t.estimated_date,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "closed_at": t.closed_at,
        "client_name": t.client.name if t.client else None,
        "assignee_name": t.assignee.full_name if t.assignee else None,
        "creator_name": t.creator.full_name if t.creator else None,
        "comment_count": len(t.comments) if t.comments else 0,
    }
    if include_comments:
        data["comments"] = [
            {
                "id": c.id,
                "ticket_id": c.ticket_id,
                "user_id": c.user_id,
                "user_name": c.user.full_name if c.user else "Sistema",
                "content": c.content,
                "is_internal": c.is_internal,
                "comment_type": c.comment_type,
                "created_at": c.created_at,
            }
            for c in (t.comments or [])
        ]
    return data


# ---- Ticket CRUD ----

@router.post("/", response_model=TicketResponse)
def create_ticket(ticket_in: TicketCreate, db: Session = Depends(get_db)):
    ticket = Ticket(
        ticket_number=_next_ticket_number(db),
        subject=ticket_in.subject,
        description=ticket_in.description,
        status=ticket_in.status or "open",
        priority=ticket_in.priority or "medium",
        category=ticket_in.category or "general",
        ticket_type=ticket_in.ticket_type,
        client_id=ticket_in.client_id,
        assigned_to=ticket_in.assigned_to,
        created_by=ticket_in.created_by,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    # Add creation comment
    comment = TicketComment(
        ticket_id=ticket.id,
        user_id=ticket_in.created_by,
        content=f"Ticket creado: {ticket_in.subject}",
        comment_type="status_change",
    )
    db.add(comment)
    db.commit()
    db.refresh(ticket)
    return _ticket_to_response(ticket)


@router.get("/", response_model=List[TicketResponse])
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    client_id: Optional[int] = None,
    assigned_to: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(Ticket).options(
        joinedload(Ticket.client),
        joinedload(Ticket.assignee),
        joinedload(Ticket.creator),
        joinedload(Ticket.comments),
    )
    if status:
        q = q.filter(Ticket.status == status)
    if priority:
        q = q.filter(Ticket.priority == priority)
    if client_id:
        q = q.filter(Ticket.client_id == client_id)
    if assigned_to:
        q = q.filter(Ticket.assigned_to == assigned_to)
    tickets = q.order_by(Ticket.updated_at.desc()).offset(skip).limit(limit).all()
    return [_ticket_to_response(t) for t in tickets]


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).options(
        joinedload(Ticket.client),
        joinedload(Ticket.assignee),
        joinedload(Ticket.creator),
        joinedload(Ticket.comments).joinedload(TicketComment.user),
    ).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _ticket_to_response(ticket, include_comments=True)


@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(ticket_id: int, ticket_in: TicketUpdate, user_id: Optional[int] = None, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    changes = []
    for field, value in ticket_in.dict(exclude_unset=True).items():
        old_val = getattr(ticket, field)
        if old_val != value:
            if field == "status":
                changes.append(f"Estado: {old_val} → {value}")
                if value in ("closed", "resolved") and not ticket.closed_at:
                    ticket.closed_at = datetime.now(timezone.utc)
                elif value not in ("closed", "resolved"):
                    ticket.closed_at = None
            elif field == "priority":
                changes.append(f"Prioridad: {old_val} → {value}")
            elif field == "assigned_to":
                changes.append(f"Asignación actualizada")
            elif field == "estimated_hours":
                changes.append(f"Horas estimadas: {value}h")
            elif field == "actual_hours":
                changes.append(f"Horas reales: {value}h")
            elif field == "estimated_date":
                changes.append(f"Fecha tentativa actualizada")
            elif field == "ticket_type":
                type_labels = {"bug": "Bug", "feature": "Requerimiento", "consultation": "Consulta"}
                changes.append(f"Tipo: {type_labels.get(str(value), value)}")
            setattr(ticket, field, value)

    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Log changes as a comment
    if changes:
        comment = TicketComment(
            ticket_id=ticket.id,
            user_id=user_id,
            content=" | ".join(changes),
            comment_type="status_change",
        )
        db.add(comment)
        db.commit()

    db.refresh(ticket)
    return _ticket_to_response(ticket)


@router.delete("/{ticket_id}")
def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    db.delete(ticket)
    db.commit()
    return {"ok": True}


# ---- Comments ----

@router.post("/{ticket_id}/comments", response_model=TicketCommentResponse)
def add_comment(ticket_id: int, comment_in: TicketCommentCreate, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=comment_in.user_id,
        content=comment_in.content,
        is_internal=comment_in.is_internal,
        comment_type=comment_in.comment_type or "comment",
    )
    db.add(comment)
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(comment)

    return {
        "id": comment.id,
        "ticket_id": comment.ticket_id,
        "user_id": comment.user_id,
        "user_name": comment.user.full_name if comment.user else "Sistema",
        "content": comment.content,
        "is_internal": comment.is_internal,
        "comment_type": comment.comment_type,
        "created_at": comment.created_at,
    }


@router.get("/{ticket_id}/comments", response_model=List[TicketCommentResponse])
def list_comments(ticket_id: int, db: Session = Depends(get_db)):
    comments = db.query(TicketComment).options(
        joinedload(TicketComment.user)
    ).filter(TicketComment.ticket_id == ticket_id).order_by(TicketComment.created_at.asc()).all()
    return [
        {
            "id": c.id,
            "ticket_id": c.ticket_id,
            "user_id": c.user_id,
            "user_name": c.user.full_name if c.user else "Sistema",
            "content": c.content,
            "is_internal": c.is_internal,
            "comment_type": c.comment_type,
            "created_at": c.created_at,
        }
        for c in comments
    ]
