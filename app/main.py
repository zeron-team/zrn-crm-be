from fastapi import FastAPI
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

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
    return {"status": "ok", "message": "Zeron CRM API is running"}

# Include routers here
from app.api.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)

import os
os.makedirs("uploads/invoices", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
