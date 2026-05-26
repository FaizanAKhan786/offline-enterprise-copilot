"""
Offline Enterprise AI Copilot — FastAPI Application
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.api.middleware.observability import ObservabilityMiddleware
from app.api.routes.agents import router as agents_router
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.misc import health_router, models_router, voice_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import async_session_factory, engine, Base
from app.services.auth.service import auth_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging(settings.log_level, json_logs=settings.environment != "development")

    # Create tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure default admin
    async with async_session_factory() as db:
        await auth_service.ensure_default_admin(db)

    yield

    # Cleanup
    from app.services.llm.service import llm_service
    await llm_service.close()
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Fully offline, enterprise-grade AI assistant platform.",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ObservabilityMiddleware)

# ── Routes ───────────────────────────────────────────────────

API_V1 = "/api/v1"

app.include_router(auth_router, prefix=API_V1)
app.include_router(chat_router, prefix=API_V1)
app.include_router(documents_router, prefix=API_V1)
app.include_router(agents_router, prefix=API_V1)
app.include_router(models_router, prefix=API_V1)
app.include_router(voice_router, prefix=API_V1)
app.include_router(health_router, prefix=API_V1)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": f"{API_V1}/health",
    }
