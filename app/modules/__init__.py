"""
ZeRoN 360° — Module Registry System
=====================================
Discovers, validates, and loads independent modules dynamically.
Each module lives in app/modules/<slug>/ and contains a manifest.py
that declares routes, models, dependencies, and metadata.
"""

import os
import importlib
import logging
from dataclasses import dataclass, field
from typing import List, Tuple, Any, Dict, Optional
from fastapi import APIRouter, FastAPI

logger = logging.getLogger(__name__)

MODULES_DIR = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ModuleManifest:
    """Declares everything a module provides."""
    name: str               # Human name: "CRM"
    slug: str               # Identifier:  "crm"
    version: str            # Semver:      "1.0.0"
    description: str        # One-liner
    icon: str = ""          # Lucide icon name for frontend
    category: str = ""      # "core", "business", "addon"
    dependencies: List[str] = field(default_factory=list)  # ["core"]
    # Each route entry: (router_instance, prefix, tags_list)
    routes: List[Tuple[APIRouter, str, List[str]]] = field(default_factory=list)
    models: List[Any] = field(default_factory=list)
    enabled: bool = True


class ModuleRegistry:
    """
    Central registry that discovers and manages all modules.
    
    Usage in main.py:
        registry = ModuleRegistry()
        registry.discover()
        registry.validate()
        registry.load_all(app, prefix="/api/v1")
    """

    def __init__(self):
        self._modules: Dict[str, ModuleManifest] = {}
        self._load_order: List[str] = []

    @property
    def modules(self) -> Dict[str, ModuleManifest]:
        return dict(self._modules)

    def register(self, manifest: ModuleManifest):
        """Register a module by its manifest."""
        if manifest.slug in self._modules:
            logger.warning(f"Module '{manifest.slug}' already registered, skipping duplicate")
            return
        self._modules[manifest.slug] = manifest
        logger.info(f"📦 Registered module: {manifest.name} v{manifest.version} [{manifest.slug}]")

    def discover(self):
        """
        Auto-discover modules by scanning app/modules/*/manifest.py
        Imports each manifest.py and calls its register(registry) function.
        """
        for entry in sorted(os.listdir(MODULES_DIR)):
            module_dir = os.path.join(MODULES_DIR, entry)
            manifest_file = os.path.join(module_dir, "manifest.py")
            if os.path.isdir(module_dir) and os.path.isfile(manifest_file):
                try:
                    mod = importlib.import_module(f"app.modules.{entry}.manifest")
                    if hasattr(mod, "register"):
                        mod.register(self)
                        logger.info(f"✅ Discovered module: {entry}")
                    else:
                        logger.warning(f"⚠️  Module {entry}/manifest.py has no register() function")
                except Exception as e:
                    logger.error(f"❌ Failed to load module {entry}: {e}")

    def validate(self) -> bool:
        """Verify all dependencies are satisfied and compute load order."""
        errors = []
        for slug, manifest in self._modules.items():
            for dep in manifest.dependencies:
                if dep not in self._modules:
                    errors.append(f"Module '{slug}' requires '{dep}' which is not registered")
                elif not self._modules[dep].enabled:
                    errors.append(f"Module '{slug}' requires '{dep}' which is disabled")

        if errors:
            for err in errors:
                logger.error(f"❌ Dependency error: {err}")
            return False

        # Topological sort for load order
        self._load_order = self._topo_sort()
        logger.info(f"📋 Load order: {' → '.join(self._load_order)}")
        return True

    def _topo_sort(self) -> List[str]:
        """Topological sort based on dependencies."""
        visited = set()
        order = []

        def visit(slug):
            if slug in visited:
                return
            visited.add(slug)
            manifest = self._modules.get(slug)
            if manifest:
                for dep in manifest.dependencies:
                    visit(dep)
                order.append(slug)

        for slug in self._modules:
            visit(slug)
        return order

    def load_all(self, app: FastAPI, prefix: str = "/api/v1"):
        """Register all module routes into the FastAPI app."""
        if not self._load_order:
            self._load_order = self._topo_sort()

        api_router = APIRouter()
        loaded_count = 0

        for slug in self._load_order:
            manifest = self._modules[slug]
            if not manifest.enabled:
                logger.info(f"⏭️  Skipping disabled module: {manifest.name}")
                continue

            for router, route_prefix, tags in manifest.routes:
                api_router.include_router(router, prefix=route_prefix, tags=tags)
                loaded_count += 1

            logger.info(
                f"🔌 Loaded module: {manifest.name} v{manifest.version} "
                f"({len(manifest.routes)} routes)"
            )

        app.include_router(api_router, prefix=prefix)
        logger.info(f"🚀 Module system ready: {len(self._load_order)} modules, {loaded_count} route groups")

    def get_module(self, slug: str) -> Optional[ModuleManifest]:
        return self._modules.get(slug)

    def is_enabled(self, slug: str) -> bool:
        mod = self._modules.get(slug)
        return mod.enabled if mod else False

    def get_status(self) -> List[dict]:
        """Return module status for the System Status page."""
        result = []
        for slug in self._load_order or sorted(self._modules.keys()):
            m = self._modules[slug]
            # Extract detailed route info
            routes_detail = []
            for router, prefix, tags in m.routes:
                endpoints = []
                for route in router.routes:
                    methods = list(getattr(route, "methods", set()))
                    path = getattr(route, "path", "")
                    name = getattr(route, "name", "")
                    endpoints.append({
                        "path": f"{prefix}{path}",
                        "methods": methods,
                        "name": name,
                    })
                routes_detail.append({
                    "prefix": prefix,
                    "tags": tags,
                    "endpoints": endpoints,
                })
            # Dependency verification
            deps_status = []
            for dep in m.dependencies:
                dep_mod = self._modules.get(dep)
                deps_status.append({
                    "slug": dep,
                    "name": dep_mod.name if dep_mod else dep,
                    "found": dep in self._modules,
                    "enabled": dep_mod.enabled if dep_mod else False,
                })
            result.append({
                "slug": m.slug,
                "name": m.name,
                "version": m.version,
                "description": m.description,
                "icon": m.icon,
                "category": m.category,
                "enabled": m.enabled,
                "dependencies": m.dependencies,
                "dependencies_status": deps_status,
                "routes_count": sum(len(rd["endpoints"]) for rd in routes_detail),
                "routes_detail": routes_detail,
            })
        return result
