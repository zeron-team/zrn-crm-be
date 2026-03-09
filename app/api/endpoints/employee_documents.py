"""Employee documents API — digital dossier (legajo digital) upload/list/delete."""
import os
import shutil
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.employee_document import EmployeeDocument
from app.models.employee import Employee
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/employees", tags=["employee_documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "uploads", "employees")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def doc_to_dict(d: EmployeeDocument):
    return {
        "id": d.id, "employee_id": d.employee_id,
        "document_type": d.document_type, "file_name": d.file_name,
        "file_size": d.file_size, "mime_type": d.mime_type,
        "notes": d.notes,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


@router.get("/{employee_id}/documents")
def list_documents(employee_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    emp = db.query(Employee).get(employee_id)
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")
    docs = db.query(EmployeeDocument).filter(EmployeeDocument.employee_id == employee_id).order_by(EmployeeDocument.created_at.desc()).all()
    return [doc_to_dict(d) for d in docs]


@router.post("/{employee_id}/documents", status_code=201)
async def upload_document(
    employee_id: int,
    document_type: str = Form(default="otro"),
    notes: str = Form(default=""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    emp = db.query(Employee).get(employee_id)
    if not emp:
        raise HTTPException(404, "Empleado no encontrado")

    # Create per-employee directory
    emp_dir = os.path.join(UPLOAD_DIR, str(employee_id))
    os.makedirs(emp_dir, exist_ok=True)

    # Save file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = f"{timestamp}_{file.filename}"
    file_path = os.path.join(emp_dir, safe_name)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    doc = EmployeeDocument(
        employee_id=employee_id,
        document_type=document_type,
        file_name=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by=current_user.id,
        notes=notes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc_to_dict(doc)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    doc = db.query(EmployeeDocument).get(doc_id)
    if not doc:
        raise HTTPException(404, "Documento no encontrado")
    # Delete file from disk
    if doc.file_path and os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"ok": True}
