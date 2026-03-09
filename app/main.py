from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.rate_limiter import RateLimitMiddleware
from app.core.redis_cache import redis_health_check

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Rate limiting middleware (must be added BEFORE CORS)
app.add_middleware(RateLimitMiddleware)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
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
        "version": "4.2.0",
        "redis": "connected" if redis_ok else "disconnected",
    }

# Include routers here
from app.api.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

import os
os.makedirs("uploads/invoices", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
