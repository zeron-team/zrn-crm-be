from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import uuid

from app.database import get_db
from app.models.company_settings import CompanySettings
from app.api.endpoints.auth import get_current_user

router = APIRouter(prefix="/company-settings", tags=["company_settings"])

UPLOAD_DIR = "/var/www/html/zeron-crm/uploads"


class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    cuit: Optional[str] = None
    slogan: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    work_start: Optional[str] = None
    work_end: Optional[str] = None
    support_start: Optional[str] = None
    support_end: Optional[str] = None
    calendar_start: Optional[str] = None
    calendar_end: Optional[str] = None
    fiscal_start_month: Optional[int] = None
    iva_condition: Optional[str] = None
    iibb_number: Optional[str] = None
    industry: Optional[str] = None
    legal_name: Optional[str] = None
    fantasy_name: Optional[str] = None
    notes: Optional[str] = None


def serialize(s: CompanySettings) -> dict:
    return {
        "id": s.id,
        "company_name": s.company_name,
        "cuit": s.cuit,
        "logo_url": s.logo_url,
        "slogan": s.slogan,
        "phone": s.phone,
        "email": s.email,
        "website": s.website,
        "address": s.address,
        "city": s.city,
        "province": s.province,
        "postal_code": s.postal_code,
        "country": s.country,
        "work_start": s.work_start,
        "work_end": s.work_end,
        "support_start": s.support_start,
        "support_end": s.support_end,
        "calendar_start": s.calendar_start,
        "calendar_end": s.calendar_end,
        "fiscal_start_month": s.fiscal_start_month,
        "iva_condition": s.iva_condition,
        "iibb_number": s.iibb_number,
        "industry": s.industry,
        "legal_name": s.legal_name,
        "fantasy_name": s.fantasy_name,
        "notes": s.notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def get_or_create(db: Session) -> CompanySettings:
    """Always work with a single settings row (id=1)."""
    settings = db.query(CompanySettings).first()
    if not settings:
        settings = CompanySettings(
            company_name="Mi Empresa",
            country="Argentina",
            work_start="09:00",
            work_end="18:00",
            support_start="08:00",
            support_end="20:00",
            calendar_start="00:00",
            calendar_end="23:00",
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("/")
def get_company_settings(db: Session = Depends(get_db)):
    """Get (or create) company settings. No auth required for read."""
    return serialize(get_or_create(db))


@router.put("/")
def update_company_settings(
    data: CompanySettingsUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update company settings. Admin only."""
    if "admin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo administradores pueden modificar la configuración")

    settings = get_or_create(db)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return serialize(settings)


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Upload company logo image."""
    if "admin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo administradores")

    # Validate file type
    allowed = {"image/png", "image/jpeg", "image/webp", "image/svg+xml", "image/gif"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {file.content_type}")

    # Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Generate unique filename
    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    filename = f"company_logo_{uuid.uuid4().hex[:8]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Save file
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Update settings
    settings = get_or_create(db)
    # Delete old logo if exists
    if settings.logo_url:
        old_path = os.path.join("/var/www/html/zeron-crm", settings.logo_url.lstrip("/"))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    settings.logo_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(settings)

    return {"logo_url": settings.logo_url, "message": "Logo actualizado"}
