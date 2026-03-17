"""Client Portal API — public endpoints for client ticket management."""
import jwt
import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models.client import Client
from app.models.ticket import Ticket, TicketComment

router = APIRouter(prefix="/portal", tags=["portal"])

SECRET_KEY = "zeron-portal-secret-key-2026"
ALGORITHM = "HS256"


# ═══ Schemas ═══

class PortalLoginRequest(BaseModel):
    email: str

class PortalLoginResponse(BaseModel):
    token: str
    client_id: int
    client_name: str
    email: str

class PortalClientInfo(BaseModel):
    id: int
    name: str
    email: str
    trade_name: Optional[str] = None
    phone: Optional[str] = None

class PortalTicketCreate(BaseModel):
    subject: str
    description: str
    priority: str = "medium"

class PortalCommentCreate(BaseModel):
    content: str

class PortalComment(BaseModel):
    id: int
    content: str
    comment_type: Optional[str] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class PortalTicketResponse(BaseModel):
    id: int
    ticket_number: str
    subject: str
    description: Optional[str] = None
    status: str
    priority: str
    category: Optional[str] = None
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None
    closed_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True

class PortalTicketDetail(PortalTicketResponse):
    comments: List[PortalComment] = []


# ═══ Auth Helpers ═══

def create_portal_token(client_id: int, email: str) -> str:
    payload = {
        "client_id": client_id,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        "type": "portal",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_portal_client(authorization: str = Header(None), db: Session = Depends(get_db)) -> Client:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token requerido")
    
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "portal":
            raise HTTPException(status_code=401, detail="Token inválido")
        client_id = payload.get("client_id")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


# ═══ Endpoints ═══

@router.post("/login", response_model=PortalLoginResponse)
def portal_login(body: PortalLoginRequest, db: Session = Depends(get_db)):
    """Login with client email — returns a portal token."""
    client = db.query(Client).filter(
        Client.email.ilike(body.email.strip())
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="No se encontró una empresa con ese email")
    
    token = create_portal_token(client.id, client.email)
    return PortalLoginResponse(
        token=token,
        client_id=client.id,
        client_name=client.name,
        email=client.email or "",
    )


@router.get("/me", response_model=PortalClientInfo)
def portal_me(client: Client = Depends(get_portal_client)):
    """Get current client info."""
    return PortalClientInfo(
        id=client.id,
        name=client.name,
        email=client.email or "",
        trade_name=getattr(client, 'trade_name', None),
        phone=client.phone,
    )


@router.get("/tickets", response_model=List[PortalTicketResponse])
def portal_list_tickets(client: Client = Depends(get_portal_client), db: Session = Depends(get_db)):
    """List all tickets for the authenticated client."""
    tickets = db.query(Ticket).filter(
        Ticket.client_id == client.id
    ).order_by(Ticket.created_at.desc()).all()
    return tickets


@router.post("/tickets", response_model=PortalTicketResponse)
def portal_create_ticket(body: PortalTicketCreate, client: Client = Depends(get_portal_client), db: Session = Depends(get_db)):
    """Create a new support ticket."""
    # Generate ticket number
    last = db.query(Ticket).order_by(Ticket.id.desc()).first()
    next_num = 1
    if last and last.ticket_number:
        import re
        m = re.search(r'(\d+)', last.ticket_number)
        if m:
            next_num = int(m.group(1)) + 1
    ticket_number = f"TK-{str(next_num).zfill(5)}"

    ticket = Ticket(
        ticket_number=ticket_number,
        subject=body.subject[:120],
        description=f"[Portal - {client.name}] {body.description}",
        status="open",
        priority=body.priority if body.priority in ("low", "medium", "high", "critical") else "medium",
        client_id=client.id,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets/{ticket_id}", response_model=PortalTicketDetail)
def portal_ticket_detail(ticket_id: int, client: Client = Depends(get_portal_client), db: Session = Depends(get_db)):
    """Get ticket detail with public comments."""
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.client_id == client.id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    # Get only non-internal comments
    comments = db.query(TicketComment).filter(
        TicketComment.ticket_id == ticket_id,
        TicketComment.is_internal == False,
    ).order_by(TicketComment.created_at.asc()).all()

    return PortalTicketDetail(
        **{c.name: getattr(ticket, c.name) for c in ticket.__table__.columns},
        comments=[PortalComment(
            id=c.id,
            content=c.content,
            comment_type=c.comment_type,
            created_at=c.created_at,
        ) for c in comments],
    )


@router.post("/tickets/{ticket_id}/comments", response_model=PortalComment)
def portal_add_comment(ticket_id: int, body: PortalCommentCreate, client: Client = Depends(get_portal_client), db: Session = Depends(get_db)):
    """Add a public comment to a ticket."""
    ticket = db.query(Ticket).filter(
        Ticket.id == ticket_id,
        Ticket.client_id == client.id,
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    comment = TicketComment(
        ticket_id=ticket_id,
        content=f"[{client.name}] {body.content}",
        is_internal=False,
        comment_type="client_reply",
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return PortalComment(
        id=comment.id,
        content=comment.content,
        comment_type=comment.comment_type,
        created_at=comment.created_at,
    )
