import logging
import json
from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.rate_limiter import RateLimitMiddleware
from app.core.redis_cache import redis_health_check

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Rate limiting middleware (must be added BEFORE CORS)
app.add_middleware(RateLimitMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    redis_ok = redis_health_check()
    return {
        "status": "ok",
        "message": "Zeron CRM API is running",
        "version": "4.3.0",
        "architecture": "modular",
        "redis": "connected" if redis_ok else "disconnected",
    }


# ═══════════════════════════════════════════════════════════
# MODULE SYSTEM — Auto-discover and load all modules
# ═══════════════════════════════════════════════════════════
from app.modules import ModuleRegistry
from app.modules.events import event_bus

registry = ModuleRegistry()
registry.discover()


def _seed_installed_modules():
    """Create installed_modules table and seed with discovered modules if empty."""
    try:
        from app.database import engine, SessionLocal
        from app.models.installed_module import InstalledModule
        from sqlalchemy import inspect

        # Create table if not exists (safe, non-destructive)
        inspector = inspect(engine)
        if "installed_modules" not in inspector.get_table_names():
            InstalledModule.__table__.create(engine, checkfirst=True)
            logger.info("📦 Created installed_modules table")

        db = SessionLocal()
        try:
            existing = {m.slug for m in db.query(InstalledModule).all()}

            for slug, manifest in registry.modules.items():
                if slug not in existing:
                    db.add(InstalledModule(
                        slug=manifest.slug,
                        name=manifest.name,
                        enabled=True,  # All enabled by default
                        version=manifest.version,
                        description=manifest.description,
                        icon=manifest.icon,
                        category=manifest.category,
                        dependencies=json.dumps(manifest.dependencies),
                        license_status="trial",
                    ))
                    logger.info(f"  → Seeded module: {manifest.name}")

            db.commit()

            # Now read DB state and apply to registry
            for row in db.query(InstalledModule).all():
                mod = registry.get_module(row.slug)
                if mod:
                    mod.enabled = row.enabled
                    if not row.enabled:
                        logger.info(f"  ⏭️  Module '{row.name}' disabled by DB config")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"⚠️  Could not seed modules (non-critical): {e}")


_seed_installed_modules()

if registry.validate():
    registry.load_all(app, prefix=settings.API_V1_STR)
else:
    logger.error("❌ Module validation failed! Falling back to legacy api.py")
    from app.api.api import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)

# Expose registry and event bus for system endpoints
app.state.module_registry = registry
app.state.event_bus = event_bus

# ═══════════════════════════════════════════════════════════
# PUBLIC PORTAL (no CRM auth required)
# ═══════════════════════════════════════════════════════════
from app.api.endpoints.portal import router as portal_router
app.include_router(portal_router, prefix=settings.API_V1_STR)


# ═══════════════════════════════════════════════════════════
# STATIC FILES
# ═══════════════════════════════════════════════════════════
import os
os.makedirs("uploads/invoices", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
