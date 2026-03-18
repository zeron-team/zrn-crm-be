"""
System Status Endpoint — Shows live status of all integrations.
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database import get_db
from app.api.endpoints.auth import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/modules")
def list_modules(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all registered modules with DB state (license, enabled)."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    registry = getattr(request.app.state, "module_registry", None)
    if not registry:
        return {"modules": []}

    # Merge registry info with DB state
    db_modules = {m.slug: m for m in db.query(InstalledModule).all()}
    result = []
    for info in registry.get_status():
        db_mod = db_modules.get(info["slug"])
        info["license_status"] = db_mod.license_status if db_mod else "trial"
        info["license_expires_at"] = str(db_mod.license_expires_at) if db_mod and db_mod.license_expires_at else None
        info["max_users"] = db_mod.max_users if db_mod else 0
        info["is_core"] = info["slug"] == "core"
        result.append(info)

    return {"modules": result}


@router.get("/status")
def system_status(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Comprehensive system status for all integrations."""
    from fastapi import HTTPException
    if "admin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo administradores")

    # Get module info
    registry = getattr(request.app.state, "module_registry", None)
    module_count = len(registry.get_status()) if registry else 0

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "8.2.5",
        "architecture": "modular",
        "modules_loaded": module_count,
        "integrations": [],
    }

    # ── 1. Backend API ──
    status["integrations"].append({
        "id": "backend",
        "name": "Backend API",
        "description": "FastAPI Application Server",
        "category": "core",
        "icon": "Server",
        "status": "ok",
        "details": {"framework": "FastAPI", "version": "8.2.5"},
    })

    # ── 2. PostgreSQL ──
    try:
        result = db.execute(text("SELECT version()")).scalar()
        pg_version = result.split(",")[0] if result else "Unknown"
        table_count = db.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
        )).scalar()
        status["integrations"].append({
            "id": "postgresql",
            "name": "PostgreSQL",
            "description": "Base de Datos Relacional",
            "category": "core",
            "icon": "Database",
            "status": "ok",
            "details": {"version": pg_version, "tables": table_count},
        })
    except Exception as e:
        status["integrations"].append({
            "id": "postgresql",
            "name": "PostgreSQL",
            "description": "Base de Datos Relacional",
            "category": "core",
            "icon": "Database",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 3. Redis ──
    try:
        from app.core.redis_cache import get_redis, redis_health_check
        redis_ok = redis_health_check()
        if redis_ok:
            r = get_redis()
            info = r.info("server")
            memory = r.info("memory")
            keys_count = r.dbsize()
            status["integrations"].append({
                "id": "redis",
                "name": "Redis Cache",
                "description": "Cache, Sesiones, Rate Limiting",
                "category": "security",
                "icon": "Zap",
                "status": "ok",
                "details": {
                    "version": info.get("redis_version", "?"),
                    "memory_used": memory.get("used_memory_human", "?"),
                    "keys": keys_count,
                    "uptime_days": info.get("uptime_in_days", 0),
                },
            })
        else:
            raise Exception("Redis not responding")
    except Exception as e:
        status["integrations"].append({
            "id": "redis",
            "name": "Redis Cache",
            "description": "Cache, Sesiones, Rate Limiting",
            "category": "security",
            "icon": "Zap",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 4. Crypto Engine (Rust or Python fallback) ──
    try:
        from app.core.security import RUST_AVAILABLE, verify_password, get_password_hash
        test_hash = get_password_hash("test")
        test_ok = verify_password("test", test_hash)
        if RUST_AVAILABLE:
            engine_name = "Rust Crypto Engine"
            crypto_details = {
                "engine": "Rust (PyO3)",
                "hash": "Argon2id",
                "jwt": "HS256 (native)",
                "encryption": "AES-256-GCM",
            }
        else:
            engine_name = "Crypto Engine (Python)"
            crypto_details = {
                "engine": "Python (fallback)",
                "hash": "bcrypt",
                "jwt": "HS256 (python-jose)",
                "encryption": "N/A (Rust required)",
            }
        status["integrations"].append({
            "id": "rust_core",
            "name": engine_name,
            "description": "Hashing, JWT, Validación criptográfica",
            "category": "security",
            "icon": "Shield",
            "status": "ok" if test_ok else "error",
            "details": crypto_details,
        })
    except Exception as e:
        status["integrations"].append({
            "id": "rust_core",
            "name": "Crypto Engine",
            "description": "Hashing, JWT, Validación criptográfica",
            "category": "security",
            "icon": "Shield",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 5. Rate Limiter ──
    status["integrations"].append({
        "id": "rate_limiter",
        "name": "Rate Limiter",
        "description": "Protección contra abuso de API",
        "category": "security",
        "icon": "ShieldAlert",
        "status": "ok" if redis_ok else "warning",
        "details": {
            "ai_chat": "10/min",
            "login": "5/min",
            "arca_emit": "30/min",
            "general": "120/min",
        },
    })

    # ── 6. Encryption ──
    enc_key_set = bool(settings.ENCRYPTION_KEY and len(settings.ENCRYPTION_KEY) == 64)
    enc_ok = False
    enc_engine = "N/A"
    try:
        if enc_key_set:
            from app.core.security import RUST_AVAILABLE as _rust_avail
            if _rust_avail:
                import rust_core as rc
                test = rc.encrypt_sensitive("test", settings.ENCRYPTION_KEY)
                decrypted = rc.decrypt_sensitive(test, settings.ENCRYPTION_KEY)
                enc_ok = decrypted == "test"
                enc_engine = "Rust AES-256-GCM"
            else:
                # Python fallback: test with Fernet symmetric encryption
                from cryptography.fernet import Fernet
                import base64, hashlib
                key = base64.urlsafe_b64encode(hashlib.sha256(bytes.fromhex(settings.ENCRYPTION_KEY)).digest())
                f = Fernet(key)
                test = f.encrypt(b"test")
                decrypted = f.decrypt(test)
                enc_ok = decrypted == b"test"
                enc_engine = "Python Fernet (AES-128-CBC)"
    except Exception:
        enc_ok = False

    status["integrations"].append({
        "id": "encryption",
        "name": "Encriptación AES-256",
        "description": "Encriptación de datos sensibles en reposo",
        "category": "security",
        "icon": "Lock",
        "status": "ok" if enc_ok else ("warning" if enc_key_set else "error"),
        "details": {
            "algorithm": enc_engine if enc_ok else "AES-256-GCM",
            "key_configured": enc_key_set,
            "functional_test": "passed" if enc_ok else "failed",
        },
    })

    # ── 7. ARCA (AFIP) ──
    try:
        from app.models.arca_config import ArcaConfig
        from app.models.invoice import Invoice
        config = db.query(ArcaConfig).first()
        if config:
            cert_exists = os.path.exists(config.cert_path or "")
            key_exists = os.path.exists(config.key_path or "")
            invoice_count = db.query(Invoice).count()
            cae_count = db.query(Invoice).filter(Invoice.cae != None).count()
            status["integrations"].append({
                "id": "arca",
                "name": "ARCA (AFIP)",
                "description": "Facturación Electrónica",
                "category": "fiscal",
                "icon": "FileCheck",
                "status": "ok" if (cert_exists and key_exists and config.is_active) else "warning",
                "details": {
                    "cuit": config.cuit,
                    "punto_venta": config.punto_vta,
                    "environment": config.environment,
                    "active": config.is_active,
                    "cert_valid": cert_exists,
                    "key_valid": key_exists,
                    "invoices": invoice_count,
                    "with_cae": cae_count,
                },
            })
        else:
            status["integrations"].append({
                "id": "arca",
                "name": "ARCA (AFIP)",
                "description": "Facturación Electrónica",
                "category": "fiscal",
                "icon": "FileCheck",
                "status": "warning",
                "details": {"error": "Sin configuración ARCA"},
            })
    except Exception as e:
        status["integrations"].append({
            "id": "arca",
            "name": "ARCA (AFIP)",
            "description": "Facturación Electrónica",
            "category": "fiscal",
            "icon": "FileCheck",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 8. Backups ──
    backup_dir = settings.BACKUP_DIR
    daily_dir = os.path.join(backup_dir, "daily")
    weekly_dir = os.path.join(backup_dir, "weekly")
    try:
        # Ensure backup subdirs exist
        os.makedirs(daily_dir, exist_ok=True)
        os.makedirs(weekly_dir, exist_ok=True)

        pg_files = sorted([f for f in os.listdir(daily_dir) if f.startswith("pg_")]) if os.path.exists(daily_dir) else []
        last_backup = pg_files[-1] if pg_files else None
        last_size = os.path.getsize(os.path.join(daily_dir, last_backup)) if last_backup else 0

        # Check if cron job is configured
        import subprocess
        cron_check = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        cron_configured = "backup.sh" in (cron_check.stdout or "")

        if last_backup and last_size > 1000:
            bk_status = "ok"
        elif os.path.exists(backup_dir):
            bk_status = "warning"  # Dir exists but no backups yet
        else:
            bk_status = "error"

        status["integrations"].append({
            "id": "backups",
            "name": "Backups Automáticos",
            "description": "pg_dump + Redis + Certificados + Uploads",
            "category": "infra",
            "icon": "HardDrive",
            "status": bk_status,
            "details": {
                "last_backup": last_backup or "Ninguno aún",
                "last_size_kb": round(last_size / 1024, 1) if last_size else 0,
                "daily_count": len(pg_files),
                "schedule": "Diario 3:00 AM UTC",
                "retention": "7 diarios, 4 semanales",
                "cron_configured": cron_configured,
                "backup_dir": backup_dir,
            },
        })
    except Exception as e:
        status["integrations"].append({
            "id": "backups",
            "name": "Backups Automáticos",
            "description": "pg_dump + Redis + Certificados + Uploads",
            "category": "infra",
            "icon": "HardDrive",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 9. Audit Logging ──
    try:
        from app.models.audit_log import AuditLog
        total_logs = db.query(AuditLog).count()
        recent_logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1).first()
        last_log_time = str(recent_logs.timestamp) if recent_logs else "Never"
        status["integrations"].append({
            "id": "audit_log",
            "name": "Audit Logging",
            "description": "Registro de acciones críticas",
            "category": "security",
            "icon": "ScrollText",
            "status": "ok",
            "details": {
                "total_entries": total_logs,
                "last_entry": last_log_time,
                "tracks": "LOGIN, LOGIN_FAILED, CREATE, UPDATE, DELETE",
            },
        })
    except Exception as e:
        status["integrations"].append({
            "id": "audit_log",
            "name": "Audit Logging",
            "description": "Registro de acciones críticas",
            "category": "security",
            "icon": "ScrollText",
            "status": "error",
            "details": {"error": str(e)},
        })

    # ── 10. AI Assistant ──
    ai_key = bool(settings.GEMINI_API_KEY)
    status["integrations"].append({
        "id": "ai_assistant",
        "name": "ZeRoN IA",
        "description": "Asistente Conversacional con IA",
        "category": "ai",
        "icon": "Brain",
        "status": "ok" if ai_key else "error",
        "details": {
            "model": settings.GEMINI_MODEL,
            "api_key_configured": ai_key,
            "tools": 18,
        },
    })

    # Summary
    statuses = [i["status"] for i in status["integrations"]]
    status["summary"] = {
        "total": len(statuses),
        "ok": statuses.count("ok"),
        "warning": statuses.count("warning"),
        "error": statuses.count("error"),
    }

    return status


# ═══════════════════════════════════════════════════════════
# MODULE MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════

@router.put("/modules/{slug}/toggle")
def toggle_module(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Enable or disable a module."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")
    if slug == "core":
        raise HTTPException(status_code=400, detail="El módulo Principal no se puede desactivar")

    from app.models.installed_module import InstalledModule
    mod = db.query(InstalledModule).filter(InstalledModule.slug == slug).first()
    if not mod:
        raise HTTPException(status_code=404, detail=f"Módulo '{slug}' no encontrado")

    mod.enabled = not mod.enabled
    db.commit()

    # Emit event
    event_bus = getattr(request.app.state, "event_bus", None)
    if event_bus:
        evt = "module.enabled" if mod.enabled else "module.disabled"
        event_bus.emit(evt, {"slug": slug, "name": mod.name}, source="system")

    return {
        "slug": slug,
        "name": mod.name,
        "enabled": mod.enabled,
        "message": f"Módulo '{mod.name}' {'activado' if mod.enabled else 'desactivado'}. Reiniciar el servidor para aplicar.",
    }


@router.put("/modules/{slug}/license")
def activate_module_license(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    license_key: str = "",
):
    """Activate a module license by providing a signed license key."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    from app.modules.licensing import validate_license

    mod = db.query(InstalledModule).filter(InstalledModule.slug == slug).first()
    if not mod:
        raise HTTPException(status_code=404, detail=f"Módulo '{slug}' no encontrado")

    if not license_key:
        raise HTTPException(status_code=400, detail="Se requiere license_key")

    # Validate the license
    info = validate_license(license_key)

    if not info.valid:
        return {
            "slug": slug,
            "name": mod.name,
            "success": False,
            "license_status": "invalid",
            "message": info.message,
        }

    # Check the license is for this module
    if info.module != slug:
        return {
            "slug": slug,
            "success": False,
            "license_status": "invalid",
            "message": f"Esta licencia es para el módulo '{info.module}', no para '{slug}'",
        }

    # Apply the license
    mod.license_key = license_key
    mod.license_status = "active"
    mod.license_expires_at = info.expires_at
    mod.max_users = info.max_users
    from datetime import datetime
    mod.updated_at = datetime.utcnow()
    db.commit()

    return {
        "slug": slug,
        "name": mod.name,
        "success": True,
        "license_status": "active",
        "plan": info.plan,
        "max_users": info.max_users,
        "expires_at": str(info.expires_at) if info.expires_at else None,
        "message": f"✅ Licencia activada para '{mod.name}' — Plan: {info.plan}, Vence: {info.expires_at.strftime('%d/%m/%Y') if info.expires_at else 'Sin vencimiento'}",
    }


@router.post("/modules/{slug}/generate-license")
def generate_module_license(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    days: int = 365,
    plan: str = "professional",
    max_users: int = 0,
    company_cuit: str = "",
):
    """
    Generate a license key for a module.
    
    - **days**: Validity in days (default 365 = 1 year)
    - **plan**: trial, starter, professional, enterprise
    - **max_users**: Max concurrent users (0 = unlimited)
    - **company_cuit**: Company CUIT for license binding
    """
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    from app.modules.licensing import generate_license
    from datetime import datetime, timedelta

    mod = db.query(InstalledModule).filter(InstalledModule.slug == slug).first()
    if not mod:
        raise HTTPException(status_code=404, detail=f"Módulo '{slug}' no encontrado")

    # Calculate expiration date
    expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")

    # Generate the signed license key
    license_key = generate_license(
        module=slug,
        company_cuit=company_cuit or "00-00000000-0",
        max_users=max_users,
        expires_at=expires_at,
        plan=plan,
    )

    # Auto-apply the license
    mod.license_key = license_key
    mod.license_status = "active"
    mod.license_expires_at = datetime.fromisoformat(expires_at)
    mod.max_users = max_users
    mod.updated_at = datetime.utcnow()
    db.commit()

    return {
        "slug": slug,
        "name": mod.name,
        "license_key": license_key,
        "license_status": "active",
        "plan": plan,
        "days": days,
        "expires_at": expires_at,
        "max_users": max_users,
        "message": f"✅ Licencia generada y activada para '{mod.name}' — {days} días, Plan: {plan}",
    }


@router.post("/modules/{slug}/activate-trial")
def activate_trial(
    slug: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    days: int = 30,
):
    """
    Activate a trial period for a module.
    
    - **days**: Trial duration (default 30 days)
    """
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    from app.modules.licensing import generate_license
    from datetime import datetime, timedelta

    mod = db.query(InstalledModule).filter(InstalledModule.slug == slug).first()
    if not mod:
        raise HTTPException(status_code=404, detail=f"Módulo '{slug}' no encontrado")

    expires_at = (datetime.utcnow() + timedelta(days=days)).strftime("%Y-%m-%d")

    license_key = generate_license(
        module=slug,
        company_cuit="trial",
        max_users=5,
        expires_at=expires_at,
        plan="trial",
    )

    mod.license_key = license_key
    mod.license_status = "trial"
    mod.license_expires_at = datetime.fromisoformat(expires_at)
    mod.max_users = 5
    mod.updated_at = datetime.utcnow()
    db.commit()

    return {
        "slug": slug,
        "name": mod.name,
        "license_status": "trial",
        "days": days,
        "expires_at": expires_at,
        "max_users": 5,
        "message": f"🔑 Trial activado para '{mod.name}' — {days} días (hasta {expires_at})",
    }


@router.post("/modules/check-expirations")
def check_expirations(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Check all module licenses and mark expired ones."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    from datetime import datetime

    modules = db.query(InstalledModule).filter(
        InstalledModule.license_expires_at.isnot(None)
    ).all()

    expired = []
    active = []
    for mod in modules:
        if mod.license_expires_at and mod.license_expires_at < datetime.utcnow():
            if mod.license_status != "expired":
                mod.license_status = "expired"
                expired.append(mod.name)
        elif mod.license_status in ("active", "trial"):
            days_left = (mod.license_expires_at - datetime.utcnow()).days if mod.license_expires_at else None
            active.append({"name": mod.name, "days_left": days_left, "status": mod.license_status})

    db.commit()

    return {
        "checked": len(modules),
        "expired": expired,
        "active": active,
        "message": f"{'⚠️ ' + str(len(expired)) + ' módulos expirados' if expired else '✅ Todos los módulos vigentes'}",
    }


@router.get("/modules/{slug}/info")
def get_module_info(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get detailed info about a specific module, including table row counts."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    from app.models.installed_module import InstalledModule
    import json as json_lib

    registry = getattr(request.app.state, "module_registry", None)
    mod = registry.get_module(slug) if registry else None
    if not mod:
        raise HTTPException(status_code=404, detail=f"Módulo '{slug}' no encontrado")

    db_mod = db.query(InstalledModule).filter(InstalledModule.slug == slug).first()

    # Table ownership per module (metadata only, tables are NOT renamed)
    MODULE_TABLES = {
        "core": ["users", "dashboard_configs", "notes", "activity_notes", "calendar_events", "chat_messages"],
        "crm": ["clients", "leads", "contacts", "quotes", "quote_items", "quote_installments", "tickets", "ticket_comments", "client_services"],
        "projects": ["projects", "project_members", "sprints", "tasks", "wiki_pages"],
        "hr": ["employees", "time_entries", "payroll_concepts", "payroll_periods", "payroll_slips", "payroll_slip_items"],
        "communications": ["email_accounts", "email_signatures", "email_messages"],
        "erp": ["invoices", "invoice_items", "invoice_iva_items", "invoice_audit_logs", "arca_configs",
                "delivery_notes", "payment_orders", "purchase_orders", "inventory_items", "warehouses",
                "exchange_rates", "service_payments", "provider_services", "providers"],
        "catalog": ["products", "categories", "families", "subcategories"],
        "system": ["audit_logs", "role_configs", "company_settings", "installed_modules"],
        "accounting": ["accounting_periods", "accounting_entries", "accounting_obligations"],
    }

    tables = MODULE_TABLES.get(slug, [])
    table_counts = {}
    for table in tables:
        try:
            count = db.execute(text(f"SELECT count(*) FROM {table}")).scalar()
            table_counts[table] = count
        except:
            table_counts[table] = -1  # table doesn't exist yet

    return {
        "slug": mod.slug,
        "name": mod.name,
        "version": mod.version,
        "description": mod.description,
        "icon": mod.icon,
        "category": mod.category,
        "dependencies": mod.dependencies,
        "enabled": mod.enabled,
        "routes_count": len(mod.routes),
        "license": {
            "status": db_mod.license_status if db_mod else "trial",
            "expires_at": str(db_mod.license_expires_at) if db_mod and db_mod.license_expires_at else None,
            "max_users": db_mod.max_users if db_mod else 0,
        },
        "tables": table_counts,
        "total_records": sum(v for v in table_counts.values() if v >= 0),
    }


@router.get("/events")
def get_events_info(
    request: Request,
    current_user=Depends(get_current_user),
):
    """Get event bus status and recent events."""
    from fastapi import HTTPException
    if "superadmin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo super administradores")

    event_bus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        return {"registered_events": {}, "recent_events": []}

    return {
        "registered_events": event_bus.get_registered_events(),
        "recent_events": event_bus.get_recent_events(),
    }
