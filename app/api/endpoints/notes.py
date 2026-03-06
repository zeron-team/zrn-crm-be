"""Notes CRUD endpoints — post-it style notes with entity associations."""
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.note import Note

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


class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    color: Optional[str] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    assigned_to: Optional[int] = None


class PositionUpdate(BaseModel):
    position_x: int
    position_y: int


# ── Endpoints ──

@router.get("")
def list_notes(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    color: Optional[str] = Query(None),
    assigned_to: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Note)
    if entity_type:
        q = q.filter(Note.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(Note.entity_id == entity_id)
    if color:
        q = q.filter(Note.color == color)
    if assigned_to is not None:
        q = q.filter(Note.assigned_to == assigned_to)
    return q.order_by(desc(Note.updated_at)).all()


@router.post("", status_code=201)
def create_note(data: NoteCreate, db: Session = Depends(get_db)):
    note = Note(**data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/{note_id}")
def get_note(note_id: int, db: Session = Depends(get_db)):
    note = db.query(Note).get(note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    return note


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
    return note


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
