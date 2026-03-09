"""Notes CRUD endpoints — post-it style notes with entity associations and privacy."""
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.note import Note
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])


# ── Schemas ──
class NoteCreate(BaseModel):
    title: str = ""
    content: Optional[str] = None
    color: str = "yellow"
    position_x: int = 0
    position_y: int = 0
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    assigned_to: Optional[int] = None
    visibility: str = "team"
    shared_with: Optional[List[int]] = None


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    assigned_to: Optional[int] = None
    visibility: Optional[str] = None
    shared_with: Optional[List[int]] = None


class PositionUpdate(BaseModel):
    position_x: int
    position_y: int


class ReorderPayload(BaseModel):
    order: List[int]


# Helper
def note_to_dict(note, db):
    from app.models.user import User
    d = {
        "id": note.id, "title": note.title, "content": note.content,
        "color": note.color, "position_x": note.position_x, "position_y": note.position_y,
        "sort_order": note.sort_order or 0,
        "entity_type": note.entity_type, "entity_id": note.entity_id,
        "created_by": note.created_by, "assigned_to": note.assigned_to,
        "visibility": note.visibility or "team",
        "shared_with": note.shared_with or [],
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }
    if note.created_by:
        u = db.query(User).filter(User.id == note.created_by).first()
        d["creator_name"] = u.full_name or u.username if u else None
    else:
        d["creator_name"] = None
    if note.assigned_to:
        u = db.query(User).filter(User.id == note.assigned_to).first()
        d["assignee_name"] = u.full_name or u.username if u else None
    else:
        d["assignee_name"] = None
    return d


# ── Static-path endpoints FIRST (before /{note_id}) ──

@router.get("")
def list_notes(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    color: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    uid = current_user.id
    q = db.query(Note)
    if entity_type:
        q = q.filter(Note.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(Note.entity_id == entity_id)
    if color:
        q = q.filter(Note.color == color)
    if assigned_to is not None:
        q = q.filter(Note.assigned_to == assigned_to)

    notes = q.order_by(Note.sort_order.asc(), desc(Note.updated_at)).all()

    result = []
    for n in notes:
        if n.visibility == "private" and n.created_by != uid:
            continue
        if n.visibility == "shared" and n.created_by != uid:
            if not n.shared_with or uid not in n.shared_with:
                continue
        result.append(note_to_dict(n, db))
    return result


@router.post("", status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    max_order = db.query(Note).count()
    note = Note(**data.model_dump(), created_by=current_user.id, sort_order=max_order)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note_to_dict(note, db)


@router.put("/reorder")
def reorder_notes(data: ReorderPayload, db: Session = Depends(get_db)):
    """Persist the visual order of notes."""
    for idx, note_id in enumerate(data.order):
        note = db.query(Note).get(note_id)
        if note:
            note.sort_order = idx
    db.commit()
    return {"ok": True}


# ── Dynamic-path endpoints (/{note_id}) ──

@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    return note_to_dict(note, db)


@router.put("/{note_id}")
def update_note(note_id: int, data: NoteUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(note, k, v)
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note_to_dict(note, db)


@router.patch("/{note_id}/position")
def update_position(note_id: int, data: PositionUpdate, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    note.position_x = data.position_x
    note.position_y = data.position_y
    db.commit()
    return {"ok": True}


@router.delete("/{note_id}")
def delete_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    db.delete(note)
    db.commit()
    return {"ok": True}
