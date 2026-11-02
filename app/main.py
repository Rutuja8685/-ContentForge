"""ContentForge FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, engine
from app.routers import auth, generate, history, templates, upload

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Gen AI Platform for Automated Content Transformation",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/auth",      tags=["auth"])
app.include_router(generate.router,  prefix="/generate",  tags=["generate"])
app.include_router(upload.router,    prefix="/upload",    tags=["upload"])
app.include_router(history.router,   prefix="/history",   tags=["history"])
app.include_router(templates.router, prefix="/templates", tags=["templates"])


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Create all DB tables on startup (idempotent)."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    """Liveness probe."""
    return {"status": "ok", "app": settings.app_name}
