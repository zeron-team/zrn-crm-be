"""
System Status Endpoint — Shows live status of all integrations.
"""

import os
import logging
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, text

from app.database import get_db
from app.api.endpoints.auth import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
def system_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Comprehensive system status for all integrations."""
    from fastapi import HTTPException
    if "admin" not in (current_user.role or ""):
        raise HTTPException(status_code=403, detail="Solo administradores")

    status = {
        "timestamp": datetime.utcnow().isoformat(),
        "version": "4.2.0",
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
        "details": {"framework": "FastAPI", "version": "4.2.0"},
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

    # ── 4. Rust Crypto Module ──
    try:
        import rust_core as rc
        # Quick functional test
        test_hash = rc.hash_password("test")
        assert rc.verify_password("test", test_hash)
        assert rc.validate_email("test@test.com")
        status["integrations"].append({
            "id": "rust_core",
            "name": "Rust Crypto Engine",
            "description": "Argon2id, JWT, AES-256-GCM, Validación",
            "category": "security",
            "icon": "Shield",
            "status": "ok",
            "details": {
                "hash": "Argon2id",
                "jwt": "HS256 (native)",
                "encryption": "AES-256-GCM",
                "validation": "CUIT, Email, HTML Sanitization",
            },
        })
    except ImportError:
        status["integrations"].append({
            "id": "rust_core",
            "name": "Rust Crypto Engine",
            "description": "Argon2id, JWT, AES-256-GCM, Validación",
            "category": "security",
            "icon": "Shield",
            "status": "error",
            "details": {"error": "Módulo rust_core no instalado"},
        })
    except Exception as e:
        status["integrations"].append({
            "id": "rust_core",
            "name": "Rust Crypto Engine",
            "description": "Argon2id, JWT, AES-256-GCM, Validación",
            "category": "security",
            "icon": "Shield",
            "status": "warning",
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
    try:
        if enc_key_set:
            import rust_core as rc
            test = rc.encrypt_sensitive("test", settings.ENCRYPTION_KEY)
            decrypted = rc.decrypt_sensitive(test, settings.ENCRYPTION_KEY)
            enc_ok = decrypted == "test"
        else:
            enc_ok = False
    except:
        enc_ok = False

    status["integrations"].append({
        "id": "encryption",
        "name": "Encriptación AES-256",
        "description": "Encriptación de datos sensibles en reposo",
        "category": "security",
        "icon": "Lock",
        "status": "ok" if enc_ok else ("warning" if enc_key_set else "error"),
        "details": {
            "algorithm": "AES-256-GCM",
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
    try:
        if os.path.exists(daily_dir):
            pg_files = sorted([f for f in os.listdir(daily_dir) if f.startswith("pg_")])
            last_backup = pg_files[-1] if pg_files else None
            last_size = os.path.getsize(os.path.join(daily_dir, last_backup)) if last_backup else 0
            status["integrations"].append({
                "id": "backups",
                "name": "Backups Automáticos",
                "description": "pg_dump + Redis + Certificados + Uploads",
                "category": "infra",
                "icon": "HardDrive",
                "status": "ok" if (last_backup and last_size > 1000) else "warning",
                "details": {
                    "last_backup": last_backup,
                    "last_size_kb": round(last_size / 1024, 1),
                    "daily_count": len(pg_files),
                    "schedule": "Diario 3:00 AM UTC",
                    "retention": "7 diarios, 4 semanales",
                },
            })
        else:
            status["integrations"].append({
                "id": "backups",
                "name": "Backups Automáticos",
                "description": "pg_dump + Redis + Certificados + Uploads",
                "category": "infra",
                "icon": "HardDrive",
                "status": "error",
                "details": {"error": "Directorio de backups no encontrado"},
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
