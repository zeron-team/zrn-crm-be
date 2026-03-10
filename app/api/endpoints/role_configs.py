from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.role_config import RoleConfig
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter(prefix="/role-configs", tags=["role_configs"])

# All available pages in the system
AVAILABLE_PAGES = [
    {"path": "/", "label": "Panel de Control", "group": "Principal"},
    {"path": "/dashboards", "label": "Dashboards", "group": "Principal"},
    {"path": "/notes", "label": "Notas", "group": "Principal"},
    {"path": "/leads", "label": "Prospectos", "group": "CRM"},
    {"path": "/quotes", "label": "Presupuestos", "group": "CRM"},
    {"path": "/clients", "label": "Cuentas", "group": "CRM"},
    {"path": "/providers", "label": "Proveedores", "group": "CRM"},
    {"path": "/contacts", "label": "Contactos", "group": "CRM"},
    {"path": "/calendar", "label": "Actividades", "group": "CRM"},
    {"path": "/support", "label": "Soporte", "group": "CRM"},
    {"path": "/sellers", "label": "Vendedores", "group": "CRM"},
    {"path": "/projects", "label": "Proyectos", "group": "Proyectos"},
    {"path": "/wiki", "label": "Wiki", "group": "Proyectos"},
    {"path": "/employees", "label": "Empleados", "group": "RRHH"},
    {"path": "/time-tracking", "label": "Fichadas", "group": "RRHH"},
    {"path": "/payroll", "label": "Liquidación de Sueldos", "group": "RRHH"},
    {"path": "/email", "label": "Email", "group": "Comunicaciones"},
    {"path": "/whatsapp", "label": "WhatsApp", "group": "Comunicaciones"},
    {"path": "/billing", "label": "Facturación", "group": "ERP"},
    {"path": "/service-purchases", "label": "Compras de Servicios", "group": "ERP"},
    {"path": "/delivery-notes", "label": "Remitos", "group": "ERP"},
    {"path": "/payment-orders", "label": "Orden de Pago", "group": "ERP"},
    {"path": "/purchase-orders", "label": "Orden de Compra", "group": "ERP"},
    {"path": "/inventory", "label": "Inventario", "group": "ERP"},
    {"path": "/warehouses", "label": "Depósitos", "group": "ERP"},
    {"path": "/exchange-rates", "label": "Tipo de Cambio", "group": "ERP"},
    {"path": "/accounting", "label": "Contabilidad", "group": "Contabilidad"},
    {"path": "/products", "label": "Productos", "group": "Catálogo"},
    {"path": "/categories", "label": "Categorías", "group": "Catálogo"},
    {"path": "/users", "label": "Usuarios", "group": "Sistema"},
    {"path": "/settings", "label": "Configuración General", "group": "Sistema"},
    {"path": "/role-permissions", "label": "Roles y Permisos", "group": "Sistema"},
    {"path": "/module-management", "label": "Gestión de Módulos", "group": "Sistema"},
]

# Default role configs seeded on first load
DEFAULT_ROLES = [
    {
        "role_name": "admin",
        "display_name": "Administrador",
        "description": "Acceso total al sistema",
        "allowed_pages": [p["path"] for p in AVAILABLE_PAGES],
        "own_data_only": False,
    },
    {
        "role_name": "user",
        "display_name": "Usuario",
        "description": "Acceso básico",
        "allowed_pages": ["/", "/dashboards", "/notes", "/calendar", "/projects", "/wiki", "/time-tracking"],
        "own_data_only": True,
    },
    {
        "role_name": "empleado",
        "display_name": "Empleado",
        "description": "Empleado con acceso a RRHH y operaciones",
        "allowed_pages": ["/", "/dashboards", "/notes", "/calendar", "/projects", "/wiki",
                          "/employees", "/time-tracking", "/support"],
        "own_data_only": True,
    },
    {
        "role_name": "vendedor",
        "display_name": "Vendedor",
        "description": "Acceso a CRM y ventas",
        "allowed_pages": ["/", "/dashboards", "/notes", "/leads", "/quotes", "/clients",
                          "/contacts", "/calendar", "/sellers", "/products", "/categories",
                          "/billing", "/time-tracking"],
        "own_data_only": False,
    },
]


class RoleConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    allowed_pages: Optional[List[str]] = None
    own_data_only: Optional[bool] = None


class RoleConfigCreate(BaseModel):
    role_name: str
    display_name: str
    description: Optional[str] = None
    allowed_pages: List[str] = []
    own_data_only: bool = True


def serialize(rc: RoleConfig) -> dict:
    return {
        "id": rc.id,
        "role_name": rc.role_name,
        "display_name": rc.display_name,
        "description": rc.description,
        "allowed_pages": rc.allowed_pages or [],
        "own_data_only": rc.own_data_only,
    }


def seed_defaults(db: Session):
    """Seed default role configs if table is empty."""
    if db.query(RoleConfig).count() == 0:
        for rd in DEFAULT_ROLES:
            db.add(RoleConfig(**rd))
        db.commit()


@router.get("/pages")
def get_available_pages():
    """Return all available pages grouped by section."""
    return AVAILABLE_PAGES


@router.get("/")
def list_role_configs(db: Session = Depends(get_db)):
    seed_defaults(db)
    roles = db.query(RoleConfig).order_by(RoleConfig.role_name).all()
    return [serialize(r) for r in roles]


@router.put("/{role_name}")
def update_role_config(role_name: str, data: RoleConfigUpdate, db: Session = Depends(get_db)):
    rc = db.query(RoleConfig).filter(RoleConfig.role_name == role_name).first()
    if not rc:
        raise HTTPException(status_code=404, detail="Role not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(rc, key, value)
    db.commit()
    db.refresh(rc)
    return serialize(rc)


BUILTIN_ROLES = {'admin', 'user', 'empleado', 'vendedor'}


@router.post("/")
def create_role_config(data: RoleConfigCreate, db: Session = Depends(get_db)):
    """Create a new custom role."""
    import re
    # Normalize role_name: lowercase, no spaces, alphanumeric + underscore
    role_name = re.sub(r'[^a-z0-9_]', '', data.role_name.lower().replace(' ', '_'))
    if not role_name:
        raise HTTPException(status_code=400, detail="Nombre de rol inválido")
    existing = db.query(RoleConfig).filter(RoleConfig.role_name == role_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un rol con el nombre '{role_name}'")
    rc = RoleConfig(
        role_name=role_name,
        display_name=data.display_name,
        description=data.description,
        allowed_pages=data.allowed_pages,
        own_data_only=data.own_data_only,
    )
    db.add(rc)
    db.commit()
    db.refresh(rc)
    return serialize(rc)


@router.delete("/{role_name}")
def delete_role_config(role_name: str, db: Session = Depends(get_db)):
    """Delete a custom role. Built-in roles cannot be deleted."""
    if role_name in BUILTIN_ROLES:
        raise HTTPException(status_code=400, detail=f"El rol '{role_name}' es un rol del sistema y no se puede eliminar")
    rc = db.query(RoleConfig).filter(RoleConfig.role_name == role_name).first()
    if not rc:
        raise HTTPException(status_code=404, detail="Role not found")
    db.delete(rc)
    db.commit()
    return {"ok": True, "deleted": role_name}


@router.get("/user-permissions/{user_id}")
def get_user_permissions(user_id: int, db: Session = Depends(get_db)):
    """Get merged permissions for a user based on all their roles."""
    from app.models.user import User
    seed_defaults(db)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_names = [r.strip() for r in (user.role or "user").split(",") if r.strip()]
    configs = db.query(RoleConfig).filter(RoleConfig.role_name.in_(role_names)).all()

    # Merge: union of all allowed pages, own_data_only = True only if ALL roles have it
    all_pages: set = set()
    all_own_data_only = True
    for cfg in configs:
        all_pages.update(cfg.allowed_pages or [])
        if not cfg.own_data_only:
            all_own_data_only = False

    # Admin override: always has all permissions
    if "admin" in role_names:
        all_pages = {p["path"] for p in AVAILABLE_PAGES}
        all_own_data_only = False

    return {
        "user_id": user_id,
        "roles": role_names,
        "allowed_pages": sorted(all_pages),
        "own_data_only": all_own_data_only,
    }
